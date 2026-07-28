from __future__ import annotations

import cgi
import json
import os
import re
import shutil
import subprocess
import threading
import traceback
import uuid
from dataclasses import asdict, dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "local_data"
INPUTS, OUTPUTS = DATA / "inputs", DATA / "outputs"
for folder in (INPUTS, OUTPUTS):
    folder.mkdir(parents=True, exist_ok=True)


@dataclass
class Job:
    id: str
    status: str = "queued"
    progress: int = 0
    stage: str = "В очереди"
    error: str | None = None
    clips: list[dict[str, Any]] = field(default_factory=list)


JOBS: dict[str, Job] = {}
JOB_CONTEXT: dict[str, dict[str, Any]] = {}
LOCK = threading.Lock()


def set_job(job_id: str, **changes: Any) -> None:
    with LOCK:
        job = JOBS[job_id]
        for key, value in changes.items():
            setattr(job, key, value)


def run(command: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=str(cwd) if cwd else None, text=True, encoding="utf-8",
                          errors="replace", stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)


def safe_name(name: str) -> str:
    stem = re.sub(r"[^\w.-]+", "_", Path(name).name, flags=re.UNICODE).strip("._")
    return stem[:100] or "video.mp4"


def acquire_source(job_id: str, config: dict[str, Any]) -> Path:
    if config["source_mode"] == "file":
        return Path(config["file_path"])
    from yt_dlp import YoutubeDL
    target = INPUTS / job_id
    target.mkdir(parents=True, exist_ok=True)
    options = {"outtmpl": str(target / "source.%(ext)s"), "format": "bv*[height<=1080]+ba/b[height<=1080]/b",
               "merge_output_format": "mp4", "noplaylist": True, "quiet": True, "no_warnings": True,
               "nocolor": True, "js_runtimes": {"node": {}},
               "extractor_args": {"youtube": {"player_client": ["mweb"]}}}
    cookie_browser = config.get("cookie_browser", "none")
    if cookie_browser in {"edge", "chrome", "firefox"}:
        options["cookiesfrombrowser"] = (cookie_browser,)
    with YoutubeDL(options) as downloader:
        info = downloader.extract_info(config["url"], download=True)
        requested = info.get("requested_downloads") or []
        candidates = [Path(item["filepath"]) for item in requested if item.get("filepath")]
        candidates += list(target.glob("source.*"))
        for candidate in candidates:
            if candidate.exists():
                return candidate
    raise RuntimeError("Видео загрузилось, но итоговый файл не найден")


def media_duration(path: Path) -> float:
    result = run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                  "-of", "default=noprint_wrappers=1:nokey=1", str(path)])
    return float(result.stdout.strip())


def transcribe(path: Path, language: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    from faster_whisper import WhisperModel
    model_name = os.environ.get("CLIPCRAFT_MODEL", "small")
    device = os.environ.get("CLIPCRAFT_DEVICE", "cpu")
    model = WhisperModel(model_name, device=device, compute_type="float16" if device == "cuda" else "int8")
    segments_iter, _ = model.transcribe(str(path), language=None if language == "auto" else language,
                                        vad_filter=True, word_timestamps=True, beam_size=5)
    segments, words = [], []
    for segment in segments_iter:
        segments.append({"start": segment.start, "end": segment.end, "text": segment.text.strip()})
        for word in segment.words or []:
            clean = word.word.strip()
            if clean:
                words.append({"start": word.start, "end": word.end, "text": clean})
    return segments, words


HOOKS = {"почему", "секрет", "ошибка", "никогда", "важно", "лучший", "правда", "как", "зачем",
         "деньги", "результат", "внимание", "смотри", "представь", "главное", "топ", "первый",
         "why", "secret", "mistake", "never", "best", "truth", "money", "watch", "the", "how"}


def choose_clips(segments: list[dict[str, Any]], duration: float, count: int, length: int) -> list[tuple[float, float]]:
    if duration <= length:
        return [(0.0, duration)]
    candidates = []
    for segment in segments:
        start = max(0.0, min(float(segment["start"]), duration - length))
        end = min(duration, start + length)
        text = segment["text"].lower()
        density = sum(1 for item in segments if start <= item["start"] < end)
        words = len(re.findall(r"\w+", text, flags=re.UNICODE))
        hooks = sum(1 for hook in HOOKS if re.search(rf"\b{re.escape(hook)}\b", text))
        punctuation = text.count("?") * 3 + text.count("!") * 2 + text.count(":")
        sentence_end = 1.5 if re.search(r"[.!?]$", text) else 0
        # Favor clear, energetic speech while avoiding clips that begin in a long pause.
        score = density * 1.8 + min(words, 30) * .15 + hooks * 4 + punctuation + sentence_end
        candidates.append((score, start, end))
    if not candidates:
        step = max(length, duration / count)
        candidates = [(1, min(i * step, duration - length), min(i * step + length, duration)) for i in range(count)]
    picked: list[tuple[float, float]] = []
    for _, start, end in sorted(candidates, reverse=True):
        if any(max(start, old_start) < min(end, old_end) - length * .25 for old_start, old_end in picked):
            continue
        picked.append((start, end))
        if len(picked) >= count:
            break
    return sorted(picked) or [(0.0, min(duration, length))]


def ass_time(seconds: float) -> str:
    seconds = max(0, seconds)
    return f"{int(seconds // 3600)}:{int(seconds % 3600 // 60):02d}:{seconds % 60:05.2f}"


def ass_escape(text: str) -> str:
    return text.replace("\\", "").replace("{", "(").replace("}", ")").replace("\n", " ")


def speech_intervals(words: list[dict[str, Any]], clip_start: float, clip_end: float, remove_silence: bool) -> list[tuple[float, float]]:
    if not remove_silence:
        return [(clip_start, clip_end)]
    selected = [word for word in words if word["end"] > clip_start and word["start"] < clip_end]
    if not selected:
        return [(clip_start, clip_end)]
    intervals: list[list[float]] = []
    for word in selected:
        start = max(clip_start, float(word["start"]) - .12)
        end = min(clip_end, float(word["end"]) + .12)
        if intervals and start - intervals[-1][1] <= .42:
            intervals[-1][1] = end
        else:
            intervals.append([start, end])
    return [(start, end) for start, end in intervals if end - start > .12]


def map_word_times(word: dict[str, Any], intervals: list[tuple[float, float]]) -> tuple[float, float]:
    cursor = 0.0
    for start, end in intervals:
        if word["end"] >= start and word["start"] <= end:
            return cursor + max(0.0, word["start"] - start), cursor + min(end - start, word["end"] - start)
        cursor += end - start
    return cursor, cursor


def make_captions(words: list[dict[str, Any]], clip_start: float, clip_end: float, target: Path,
                  style: str = "viral", intervals: list[tuple[float, float]] | None = None) -> None:
    intervals = intervals or [(clip_start, clip_end)]
    selected = [word for word in words if word["end"] > clip_start and word["start"] < clip_end]
    timed_words = []
    for word in selected:
        if len(intervals) == 1 and intervals[0] == (clip_start, clip_end):
            start, end = word["start"] - clip_start, word["end"] - clip_start
        else:
            start, end = map_word_times(word, intervals)
        timed_words.append({**word, "render_start": start, "render_end": end})
    groups, current = [], []
    for word in timed_words:
        if current and (len(current) >= 4 or word["render_end"] - current[0]["render_start"] > 2.2):
            groups.append(current)
            current = []
        current.append(word)
    if current:
        groups.append(current)
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Viral,Arial,74,&H003DFFC9,&H00FFFFFF,&H00000000,&H66000000,-1,0,0,0,100,100,1,0,1,7,2,2,65,65,360,1
Style: Clean,Arial,58,&H00FFFFFF,&H00FFFFFF,&H00000000,&H66000000,-1,0,0,0,100,100,0,0,1,5,1,2,65,65,300,1
Style: Neon,Arial,68,&H0000FFFF,&H00FFFFFF,&H00000000,&H66000000,-1,0,0,0,100,100,1,0,1,7,2,2,65,65,340,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [header]
    for group in groups:
        start = max(0, group[0]["render_start"])
        end = min(sum(b - a for a, b in intervals), group[-1]["render_end"] + .08)
        karaoke = [r"{\kf" + str(max(5, round((word["render_end"] - word["render_start"]) * 100))) + "}" +
                   ass_escape(word["text"].upper()) for word in group]
        chosen_style = {"clean": "Clean", "neon": "Neon"}.get(style, "Viral")
        lines.append(f"Dialogue: 0,{ass_time(start)},{ass_time(end)},{chosen_style},,0,0,0,,{' '.join(karaoke)}\n")
    target.write_text("".join(lines), encoding="utf-8-sig")


def render_clip(source: Path, start: float, end: float, ass_file: Path, target: Path,
                remove_silence: bool = False, style: str = "viral", words: list[dict[str, Any]] | None = None) -> float:
    intervals = speech_intervals(words or [], start, end, remove_silence)
    parts: list[str] = []
    for index, (part_start, part_end) in enumerate(intervals):
        parts.append(f"[0:v]trim=start={part_start:.3f}:end={part_end:.3f},setpts=PTS-STARTPTS[v{index}];")
        parts.append(f"[0:a]atrim=start={part_start:.3f}:end={part_end:.3f},asetpts=PTS-STARTPTS[a{index}];")
    joined = "".join(f"[v{i}][a{i}]" for i in range(len(intervals)))
    parts.append(f"{joined}concat=n={len(intervals)}:v=1:a=1[cv][ca];")
    filters = ("".join(parts) + "[cv]split=2[background][foreground];"
               "[background]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,gblur=sigma=35[blurred];"
               "[foreground]scale=1080:1920:force_original_aspect_ratio=decrease[main];"
               "[blurred][main]overlay=(W-w)/2:(H-h)/2[composed];"
               f"[composed]subtitles=filename='{ass_file.name}'[video]")
    run(["ffmpeg", "-y", "-i", str(source), "-filter_complex", filters, "-map", "[video]", "-map", "[ca]", "-c:v", "libx264",
         "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
         "-movflags", "+faststart", str(target)], cwd=ass_file.parent)
    return sum(end - start for start, end in intervals)


def process_job(job_id: str, config: dict[str, Any]) -> None:
    try:
        if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
            raise RuntimeError("FFmpeg не найден. Запусти setup.ps1 и перезапусти программу.")
        set_job(job_id, status="working", progress=5, stage="Получаю исходное видео")
        source = acquire_source(job_id, config)
        duration = media_duration(source)
        set_job(job_id, progress=18, stage="Распознаю речь")
        segments, words = transcribe(source, config["language"])
        set_job(job_id, progress=50, stage="Выбираю лучшие моменты")
        ranges = choose_clips(segments, duration, config["clip_count"], config["clip_length"])
        JOB_CONTEXT[job_id] = {"source": source, "words": words, "config": config, "ranges": ranges}
        out_dir = OUTPUTS / job_id
        out_dir.mkdir(parents=True, exist_ok=True)
        clips = []
        style = config.get("caption_style", "viral")
        remove_silence = config.get("remove_silence", False)
        for index, (start, end) in enumerate(ranges, 1):
            set_job(job_id, progress=50 + round(index / len(ranges) * 47), stage=f"Собираю клип {index} из {len(ranges)}")
            captions, target = out_dir / f"captions_{index:02d}.ass", out_dir / f"clip_{index:02d}.mp4"
            intervals = speech_intervals(words, start, end, remove_silence)
            make_captions(words, start, end, captions, style, intervals)
            output_duration = render_clip(source, start, end, captions, target, remove_silence, style, words)
            clips.append({"name": target.name, "path": str(target), "start": start, "end": end,
                          "duration": output_duration, "download_url": f"/api/download/{job_id}/{target.name}",
                          "edit_url": f"/api/jobs/{job_id}/clips/{index - 1}"})
        set_job(job_id, status="done", progress=100, stage="Готово", clips=clips)
    except Exception as exc:
        traceback.print_exc()
        clean_error = re.sub(r"\x1b\[[0-9;]*m", "", str(exc))
        if "Could not copy Chrome cookie database" in clean_error:
            clean_error = "Chrome блокирует cookie. Откройте ClipTime в Edge, полностью закройте Chrome (включая фоновые процессы), выберите Google Chrome и повторите."
        elif "Could not copy Edge cookie database" in clean_error:
            clean_error = "Edge блокирует cookie. Откройте ClipTime в Chrome, полностью закройте Edge (включая фоновые процессы), выберите Microsoft Edge и повторите."
        elif "Sign in to confirm" in clean_error:
            clean_error = "YouTube требует авторизацию. Выберите Edge или Chrome в настройке авторизации и убедитесь, что в этом браузере выполнен вход в YouTube."
        set_job(job_id, status="error", stage="Ошибка обработки", error=clean_error)


class Handler(BaseHTTPRequestHandler):
    server_version = "ClipTime/0.1"

    def cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def json_response(self, status: int, payload: Any) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.cors()
        self.end_headers()

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/health":
            self.json_response(200, {"ok": True, "ffmpeg": bool(shutil.which("ffmpeg"))})
            return
        if path.startswith("/api/jobs/"):
            job_id = path.rsplit("/", 1)[-1]
            with LOCK:
                job = JOBS.get(job_id)
                payload = asdict(job) if job else None
            self.json_response(200 if payload else 404, payload or {"error": "Задача не найдена"})
            return
        if path.startswith("/api/download/"):
            parts = [unquote(part) for part in path.split("/") if part]
            if len(parts) == 4:
                job_id, filename = parts[2], safe_name(parts[3])
                target = OUTPUTS / job_id / filename
                if target.is_file() and target.suffix.lower() == ".mp4":
                    self.send_response(200)
                    self.cors()
                    self.send_header("Content-Type", "video/mp4")
                    self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
                    self.send_header("Content-Length", str(target.stat().st_size))
                    self.end_headers()
                    with target.open("rb") as stream:
                        shutil.copyfileobj(stream, self.wfile)
                    return
            self.json_response(404, {"error": "Файл не найден"})
            return
        self.json_response(404, {"error": "Не найдено"})

    def do_POST(self) -> None:
        request_path = urlparse(self.path).path
        edit_match = re.fullmatch(r"/api/jobs/([a-f0-9]+)/clips/(\d+)", request_path)
        if edit_match:
            try:
                job_id, clip_index = edit_match.group(1), int(edit_match.group(2))
                context = JOB_CONTEXT.get(job_id)
                job = JOBS.get(job_id)
                if not context or not job or clip_index >= len(job.clips):
                    raise ValueError("Клип больше недоступен для редактирования")
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length) or b"{}")
                old = job.clips[clip_index]
                start = max(0.0, float(payload.get("start", old["start"])))
                end = min(media_duration(context["source"]), float(payload.get("end", old["end"])))
                if end - start < 5:
                    raise ValueError("Минимальная длина клипа — 5 секунд")
                set_job(job_id, status="working", progress=50, stage="Пересобираю клип")
                context["ranges"][clip_index] = (start, end)
                out_dir = OUTPUTS / job_id
                index = clip_index + 1
                captions = out_dir / f"captions_{index:02d}.ass"
                target = out_dir / f"clip_{index:02d}.mp4"
                config = context["config"]
                intervals = speech_intervals(context["words"], start, end, config.get("remove_silence", False))
                make_captions(context["words"], start, end, captions, config.get("caption_style", "viral"), intervals)
                output_duration = render_clip(context["source"], start, end, captions, target,
                                              config.get("remove_silence", False), config.get("caption_style", "viral"), context["words"])
                old.update({"start": start, "end": end, "duration": output_duration})
                set_job(job_id, status="done", progress=100, stage="Готово", clips=job.clips)
                self.json_response(200, asdict(job))
            except Exception as exc:
                self.json_response(400, {"error": str(exc)})
            return
        if request_path != "/api/jobs":
            self.json_response(404, {"error": "Не найдено"})
            return
        try:
            form = cgi.FieldStorage(fp=self.rfile, headers=self.headers, environ={"REQUEST_METHOD": "POST",
                "CONTENT_TYPE": self.headers.get("Content-Type", ""), "CONTENT_LENGTH": self.headers.get("Content-Length", "0")})
            job_id, mode = uuid.uuid4().hex[:12], form.getfirst("source_mode", "url")
            config: dict[str, Any] = {"source_mode": mode, "url": form.getfirst("url", "").strip(),
                "clip_count": max(1, min(20, int(form.getfirst("clip_count", "6")))),
                "clip_length": max(15, min(90, int(form.getfirst("clip_length", "35")))),
                "language": form.getfirst("language", "auto"),
                "cookie_browser": form.getfirst("cookie_browser", "none"),
                "caption_style": form.getfirst("caption_style", "viral"),
                "remove_silence": form.getfirst("remove_silence", "false").lower() == "true"}
            if mode == "file":
                upload = form["file"] if "file" in form else None
                if upload is None or not getattr(upload, "file", None):
                    raise ValueError("Выбери видеофайл")
                folder = INPUTS / job_id
                folder.mkdir(parents=True, exist_ok=True)
                target = folder / safe_name(upload.filename or "video.mp4")
                with target.open("wb") as output:
                    shutil.copyfileobj(upload.file, output)
                config["file_path"] = str(target)
            elif not config["url"].startswith(("http://", "https://")):
                raise ValueError("Вставь корректную ссылку на видео")
            job = Job(id=job_id)
            with LOCK:
                JOBS[job_id] = job
            threading.Thread(target=process_job, args=(job_id, config), daemon=True).start()
            self.json_response(202, asdict(job))
        except Exception as exc:
            self.json_response(400, {"error": str(exc)})

    def log_message(self, format: str, *args: Any) -> None:
        print(f"[ClipTime] {self.address_string()} - {format % args}")


if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("BACKEND_PORT", "8765"))
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"ClipTime engine: http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
