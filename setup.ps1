$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

Write-Host "[1/3] Checking Python 3.12..." -ForegroundColor Cyan
if (-not (Get-Command py -ErrorAction SilentlyContinue)) { throw "Install Python 3.12 from python.org" }
if (-not (Test-Path ".venv")) { & py -3.12 -m venv .venv }
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt

Write-Host "[2/3] Checking FFmpeg..." -ForegroundColor Cyan
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        & winget install --id Gyan.FFmpeg.Shared -e --accept-package-agreements --accept-source-agreements
        $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
        Write-Host "FFmpeg installed. Restart Windows if it is not detected." -ForegroundColor Yellow
    } else { throw "FFmpeg is missing. Install it from ffmpeg.org and add it to PATH." }
}

Write-Host "[3/3] Preparing interface..." -ForegroundColor Cyan
$ProviderServer = Join-Path $ProjectRoot "vendor\bgutil-ytdlp-pot-provider\server"
if (-not (Test-Path $ProviderServer)) {
    Write-Host "Downloading YouTube token provider..." -ForegroundColor Cyan
    New-Item -ItemType Directory -Force (Join-Path $ProjectRoot "vendor") | Out-Null
    & git clone --depth 1 https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git (Join-Path $ProjectRoot "vendor\bgutil-ytdlp-pot-provider")
}
$FFmpeg = Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\Gyan.FFmpeg.Shared_*" -Recurse -Filter "ffmpeg.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
if ($FFmpeg) { $env:Path = $FFmpeg.DirectoryName + ";" + $env:Path }
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) { throw "Install Node.js LTS from nodejs.org" }
& npm install --ignore-scripts

if (Test-Path $ProviderServer) {
    Write-Host "Preparing YouTube PO-token provider..." -ForegroundColor Cyan
    Push-Location $ProviderServer
    & npm ci
    & npm approve-scripts canvas @swc/core
    & npm rebuild canvas @swc/core
    & npx tsc
    Pop-Location
}
Write-Host "Ready. Run start.ps1" -ForegroundColor Green
