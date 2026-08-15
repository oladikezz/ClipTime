<div align="center">
  
# 🎬 ClipTime Local

**Local tool for converting long videos into vertical 9:16 clips with dynamic subtitles**

[🇺🇸 English](README.md) | [🇷🇺 Русский](README.ru.md) | [🇨🇳 中文](README.zh-CN.md)

[![PowerShell](https://img.shields.io/badge/PowerShell-Script-5391FE.svg?style=for-the-badge&logo=powershell)](https://learn.microsoft.com/en-us/powershell/)

</div>

---

ClipTime Local is an automated program that transforms standard wide-aspect long videos into highly engaging vertical clips (9:16) optimized for TikTok, YouTube Shorts, and Instagram Reels. 

The tool intelligently crops the video, applies a blurred background fill for the remaining space, and automatically generates dynamic, on-screen subtitles using Whisper AI.

## ✨ Features

- 📱 **Vertical Formatting:** Converts wide videos to a 9:16 aspect ratio perfectly suited for mobile viewing.
- 🌫️ **Blurred Backgrounds:** Automatically fills the empty top and bottom spaces of the vertical canvas with a blurred version of the video.
- 💬 **Dynamic Subtitles:** Generates accurate on-screen text overlays using Whisper AI.
- ⚡ **Local Processing:** Runs entirely on your local machine—no need to upload large video files to the cloud.
- 🎛️ **Adjustable Accuracy:** Switch between different AI models (`small`, `base`, `medium`) to balance speed and accuracy.

## 🚀 Quick Start

1. Right-click on `setup.ps1` and select **Run with PowerShell**. This will install the necessary dependencies.
2. Once installed, run `start.ps1` in the same way.
3. The web interface will open automatically in your browser at `http://localhost:3000`.

*If PowerShell blocks the execution due to security policies, open PowerShell in the project folder and run:*
```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
powershell -ExecutionPolicy Bypass -File .\start.ps1
```

## ⚙️ Configuration

Finished videos are automatically saved to `local_data/outputs/<task-number>`.

By default, the AI speech recognition uses the `small` model running on the CPU. 
- For **faster** processing (but lower accuracy), set the environment variable: `CLIPCRAFT_MODEL=base`
- For **higher accuracy** (slower processing), set: `CLIPCRAFT_MODEL=medium`

> **Disclaimer:** Please ensure you only download, process, and distribute videos for which you have explicit permission or hold the copyright.
