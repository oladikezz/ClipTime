$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot
$env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
$FFmpeg = Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\Gyan.FFmpeg.Shared_*" -Recurse -Filter "ffmpeg.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
if ($FFmpeg) { $env:Path = $FFmpeg.DirectoryName + ";" + $env:Path }
if (-not (Test-Path ".venv\Scripts\python.exe")) { throw "Run setup.ps1 first" }

$Provider = $null
$ProviderScript = Join-Path $ProjectRoot "vendor\bgutil-ytdlp-pot-provider\server\build\main.js"
$ProviderRunning = netstat -ano | Select-String ':4416\s+.*LISTENING'
if ((Test-Path $ProviderScript) -and (-not $ProviderRunning)) {
    $ProviderRoot = Split-Path (Split-Path $ProviderScript -Parent) -Parent
    $Provider = Start-Process -FilePath "node.exe" -ArgumentList "build\main.js" -WorkingDirectory $ProviderRoot -PassThru -WindowStyle Hidden
}
$Engine = Start-Process -FilePath ".venv\Scripts\python.exe" -ArgumentList "backend\server.py" -WorkingDirectory $ProjectRoot -PassThru -WindowStyle Hidden
try {
    $Interface = Start-Process -FilePath "npm.cmd" -ArgumentList "run", "dev" -WorkingDirectory $ProjectRoot -PassThru -NoNewWindow
    Start-Sleep -Seconds 4
    Start-Process "http://localhost:3000" | Out-Null
    Wait-Process -Id $Interface.Id
} finally {
    if ($Interface -and -not $Interface.HasExited) { Stop-Process -Id $Interface.Id }
    if ($Engine -and -not $Engine.HasExited) { Stop-Process -Id $Engine.Id }
    if ($Provider -and -not $Provider.HasExited) { Stop-Process -Id $Provider.Id }
}
