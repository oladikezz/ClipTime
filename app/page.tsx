"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

const API = "http://127.0.0.1:8765/api";

type Job = {
  id: string;
  status: "queued" | "working" | "done" | "error";
  progress: number;
  stage: string;
  clips?: { name: string; path: string; download_url: string; edit_url?: string; start?: number; end?: number; duration?: number }[];
  error?: string;
};

function formatSize(bytes: number) {
  if (!bytes) return "";
  const units = ["Б", "КБ", "МБ", "ГБ"];
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), 3);
  return `${(bytes / 1024 ** i).toFixed(i ? 1 : 0)} ${units[i]}`;
}

export default function Home() {
  const [sourceMode, setSourceMode] = useState<"url" | "file">("url");
  const [url, setUrl] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [clipCount, setClipCount] = useState(6);
  const [clipLength, setClipLength] = useState(35);
  const [language, setLanguage] = useState("auto");
  const [captionStyle, setCaptionStyle] = useState("viral");
  const [removeSilence, setRemoveSilence] = useState(true);
  const [cookieBrowser, setCookieBrowser] = useState("none");
  const [currentBrowser, setCurrentBrowser] = useState<"edge" | "chrome" | "firefox" | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [edits, setEdits] = useState<Record<number, { start: string; end: string }>>({});
  const [savingClip, setSavingClip] = useState<number | null>(null);
  const [online, setOnline] = useState<boolean | null>(null);
  const busy = job?.status === "queued" || job?.status === "working";

  useEffect(() => {
    fetch(`${API}/health`)
      .then((r) => setOnline(r.ok))
      .catch(() => setOnline(false));
    const agent = navigator.userAgent;
    const detected = agent.includes("Edg/") ? "edge" : agent.includes("Firefox/") ? "firefox" : agent.includes("Chrome/") ? "chrome" : null;
    setCurrentBrowser(detected);
  }, []);

  useEffect(() => {
    if (!job || !busy) return;
    const timer = window.setInterval(async () => {
      try {
        const res = await fetch(`${API}/jobs/${job.id}`);
        if (res.ok) setJob(await res.json());
      } catch {
        setOnline(false);
      }
    }, 1500);
    return () => window.clearInterval(timer);
  }, [job?.id, busy]);

  const canSubmit = useMemo(
    () => !busy && (sourceMode === "url" ? /^https?:\/\//.test(url) : Boolean(file)),
    [busy, file, sourceMode, url],
  );

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!canSubmit) return;
    const body = new FormData();
    body.set("source_mode", sourceMode);
    body.set("clip_count", String(clipCount));
    body.set("clip_length", String(clipLength));
    body.set("language", language);
    body.set("caption_style", captionStyle);
    body.set("remove_silence", String(removeSilence));
    body.set("cookie_browser", cookieBrowser);
    if (sourceMode === "url") body.set("url", url);
    if (file) body.set("file", file);
    try {
      const res = await fetch(`${API}/jobs`, { method: "POST", body });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Не удалось запустить обработку");
      setOnline(true);
      setEdits({});
      setJob(data);
    } catch (error) {
      setJob({ id: "", status: "error", progress: 0, stage: "Ошибка", error: String(error) });
    }
  }

  function editValue(index: number, key: "start" | "end", fallback = 0) {
    return edits[index]?.[key] ?? String(Math.round(fallback));
  }

  async function saveEdit(index: number, clip: NonNullable<Job["clips"]>[number]) {
    if (!job?.id || !clip.edit_url) return;
    setSavingClip(index);
    try {
      const response = await fetch(`${API}${clip.edit_url}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ start: Number(editValue(index, "start", clip.start)), end: Number(editValue(index, "end", clip.end)) }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Не удалось пересобрать клип");
      setJob(data);
    } catch (error) {
      setJob((current) => current ? { ...current, status: "error", error: String(error) } : current);
    } finally {
      setSavingClip(null);
    }
  }

  return (
    <main>
      <header className="topbar">
        <a className="brand" href="#"><span className="brandMark">C</span> CLIPTIME <i>LOCAL</i></a>
        <div className="status"><span className={online ? "dot online" : "dot"} />{online ? "Движок готов" : "Движок не запущен"}</div>
      </header>

      <section className="hero">
        <p className="eyebrow">ЛИЧНАЯ СТУДИЯ КОРОТКИХ ВИДЕО</p>
        <h1>Один ролик.<br /><span>Много клипов.</span></h1>
        <p className="lede">Превращай длинные видео в готовые TikTok, Reels и Shorts — вертикальный кадр, блюр-фон и динамические субтитры.</p>
      </section>

      <section className="workspace">
        <form className="panel controlPanel" onSubmit={submit}>
          <div className="panelTitle"><span>01</span><h2>Исходное видео</h2></div>
          <div className="tabs">
            <button type="button" className={sourceMode === "url" ? "active" : ""} onClick={() => setSourceMode("url")}>Ссылка</button>
            <button type="button" className={sourceMode === "file" ? "active" : ""} onClick={() => setSourceMode("file")}>Файл</button>
          </div>

          {sourceMode === "url" ? (
            <label className="field"><span>Ссылка на видео</span><input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://youtube.com/watch?v=..." /></label>
          ) : (
            <label className="dropzone">
              <input type="file" accept="video/*" onChange={(e) => setFile(e.target.files?.[0] || null)} />
              <b>{file ? file.name : "Выбрать видео"}</b>
              <span>{file ? formatSize(file.size) : "MP4, MOV, MKV или WEBM"}</span>
            </label>
          )}

          <div className="panelTitle settingsTitle"><span>02</span><h2>Настройки</h2></div>
          <div className="settingsGrid">
            <label className="field"><span>Количество клипов</span><input type="number" min="1" max="20" value={clipCount} onChange={(e) => setClipCount(Number(e.target.value))} /></label>
            <label className="field"><span>Длина, секунд</span><input type="number" min="15" max="90" value={clipLength} onChange={(e) => setClipLength(Number(e.target.value))} /></label>
            <label className="field full"><span>Язык речи</span><select value={language} onChange={(e) => setLanguage(e.target.value)}><option value="auto">Определить автоматически</option><option value="ru">Русский</option><option value="en">English</option><option value="az">Azərbaycan</option></select></label>
            <label className="field"><span>Стиль субтитров</span><select value={captionStyle} onChange={(e) => setCaptionStyle(e.target.value)}><option value="viral">Viral — крупные слова</option><option value="clean">Clean — минимальный</option><option value="neon">Neon — яркий</option></select></label>
            <label className="checkField"><input type="checkbox" checked={removeSilence} onChange={(e) => setRemoveSilence(e.target.checked)} /><span><b>Убирать паузы</b><small>Сжатие длинных пауз в речи</small></span></label>
            {sourceMode === "url" && <label className="field full"><span>Способ загрузки YouTube</span><select value={cookieBrowser} onChange={(e) => setCookieBrowser(e.target.value)}><option value="none">Автоматически — без cookie</option><option value="edge" disabled={currentBrowser === "edge"}>Резерв: Microsoft Edge{currentBrowser === "edge" ? " — сейчас открыт" : ""}</option><option value="chrome" disabled={currentBrowser === "chrome"}>Резерв: Google Chrome{currentBrowser === "chrome" ? " — сейчас открыт" : ""}</option><option value="firefox" disabled={currentBrowser === "firefox"}>Резерв: Mozilla Firefox{currentBrowser === "firefox" ? " — сейчас открыт" : ""}</option></select><small className="fieldNote">Автоматический режим использует локальный PO-token provider. Браузер нужен только для закрытых или возрастных видео.</small></label>}
          </div>

          <button className="primary" disabled={!canSubmit}>{busy ? "Обрабатываю…" : "СОЗДАТЬ КЛИПЫ"}<span>→</span></button>
          {!online && <p className="hint">Запусти файл <strong>start.ps1</strong>, затем обнови страницу.</p>}
        </form>

        <div className="panel resultPanel">
          <div className="phone">
            <div className="phoneVideo">
              <div className="blur blurTop" /><div className="mockFrame"><span>9:16</span></div><div className="blur blurBottom" />
              <div className="caption"><em>СОЗДАВАЙ</em><br />КОНТЕНТ БЫСТРЕЕ</div>
            </div>
          </div>
          <div className="resultCopy">
            <p className="eyebrow">ПРЕДПРОСМОТР</p>
            <h2>{job?.status === "done" ? "Клипы готовы" : job?.status === "error" ? "Что-то пошло не так" : busy ? job.stage : "Твой результат"}</h2>
            {job ? (
              <>
                <div className="progress"><i style={{ width: `${job.progress}%` }} /></div>
                <p>{job.error || `${job.progress}% · ${job.stage}`}</p>
                {job.clips?.length ? <div className="clipEditor">{job.clips.map((clip, index) => <div className="clipRow" key={clip.name}><video controls preload="metadata" src={`http://127.0.0.1:8765${clip.download_url}`} /><div className="clipMeta"><b>Клип {index + 1}</b><div className="trimInputs"><label>от<input type="number" min="0" step="1" value={editValue(index, "start", clip.start)} onChange={(e) => setEdits((all) => ({ ...all, [index]: { start: e.target.value, end: editValue(index, "end", clip.end) } }))} /></label><label>до<input type="number" min="1" step="1" value={editValue(index, "end", clip.end)} onChange={(e) => setEdits((all) => ({ ...all, [index]: { start: editValue(index, "start", clip.start), end: e.target.value } }))} /></label></div><div className="clipActions"><button type="button" onClick={() => saveEdit(index, clip)} disabled={savingClip === index}>{savingClip === index ? "Сохраняю…" : "Применить"}</button><a href={`http://127.0.0.1:8765${clip.download_url}`}>Скачать ↓</a></div></div></div>)}</div> : null}
              </>
            ) : <p>После обработки здесь появятся готовые вертикальные видео.</p>}
          </div>
        </div>
      </section>

      <footer><span>100% локальная обработка</span><span>Без загрузки в облако</span><span>Готово для 1080 × 1920</span></footer>
    </main>
  );
}
