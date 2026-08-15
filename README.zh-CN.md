<div align="center">
  
# 🎬 ClipTime Local

**将长视频转换为带动态字幕的 9:16 竖屏短片的本地工具**

[🇺🇸 English](README.md) | [🇷🇺 Русский](README.ru.md) | [🇨🇳 中文](README.zh-CN.md)

[![PowerShell](https://img.shields.io/badge/PowerShell-脚本-5391FE.svg?style=for-the-badge&logo=powershell)](https://learn.microsoft.com/zh-cn/powershell/)

</div>

---

ClipTime Local 是一款自动化本地程序，旨在将标准的宽屏长视频转换为高互动性的竖屏短片 (9:16)，完美适配 TikTok、YouTube Shorts 和 Instagram Reels。

该工具不仅能智能裁剪视频，还会自动使用模糊的视频背景填充画面的上下空白区域，并借助 Whisper AI 自动生成动态的屏幕字幕。

## ✨ 核心特性

- 📱 **竖屏格式化：** 将宽屏视频转换为适合移动端观看的 9:16 比例。
- 🌫️ **模糊背景填充：** 自动将视频画面的上下空白区域填充为带有模糊效果的视频背景。
- 💬 **动态字幕：** 使用 Whisper AI 生成精准的屏幕滚动文本。
- ⚡ **本地处理：** 完全在您的本地计算机上运行——无需向云端上传庞大的视频文件。
- 🎛️ **AI 精度调节：** 可在不同的 AI 模型（`small`, `base`, `medium`）之间切换，以平衡处理速度与识别精度。

## 🚀 快速开始

1. 右键点击 `setup.ps1`，然后选择 **使用 PowerShell 运行 (Run with PowerShell)** 以安装必要的依赖项。
2. 安装完成后，以相同的方式运行 `start.ps1`。
3. 程序的 Web 界面将自动在浏览器中打开，地址为 `http://localhost:3000`。

*如果 PowerShell 出于安全策略拦截了脚本运行，请在项目文件夹中打开 PowerShell 并执行以下命令：*
```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
powershell -ExecutionPolicy Bypass -File .\start.ps1
```

## ⚙️ 配置与输出

处理完成的视频将自动保存到 `local_data/outputs/<任务编号>` 目录中。

默认情况下，语音识别使用基于 CPU 运行的 `small` 模型。
- 如需 **更快的处理速度**（但精度较低），请设置环境变量：`CLIPCRAFT_MODEL=base`
- 如需 **更高的识别精度**（处理速度较慢），请设置环境变量：`CLIPCRAFT_MODEL=medium`

> **免责声明：** 请确保您仅下载、处理和分发您拥有明确许可或版权的视频内容。
