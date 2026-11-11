<#
.SYNOPSIS
  One-click start (or stop) of the whole TwinGuard AI demo: AI service + GPU worker + live forecasts, the UI, and the browser.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File start_twinguard.ps1          # start everything and open the browser
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File start_twinguard.ps1 -Stop    # stop everything
#>
param(
    [switch]$Stop,
    [int]$UiPort = 5173,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$Frontend = Join-Path $Root "frontend"
$LiveScript = Join-Path $Root "services\ai-service\start_live.ps1"
$LogDir = Join-Path $Root "data\features\v3\logs"
$UiUrl = "http://localhost:$UiPort"

function Test-Url([string]$Url) {
    try { $null = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 2; return $true } catch { return $false }
}

function Wait-Url([string]$Url, [int]$Seconds, [string]$Name) {
    Write-Host -NoNewline "Waiting for $Name "
    for ($i = 0; $i -lt $Seconds; $i++) {
        if (Test-Url $Url) { Write-Host " ready."; return $true }
        Write-Host -NoNewline "."
        Start-Sleep -Seconds 1
    }
    Write-Host " timed out."
    return $false
}

function Get-UiProcesses {
    Get-CimInstance Win32_Process -Filter "Name='node.exe'" |
        Where-Object { $_.CommandLine -match 'vite' -and $_.CommandLine -match [regex]::Escape($Frontend) }
}

if ($Stop) {
    Write-Host "Stopping TwinGuard AI..."
    $ui = @(Get-UiProcesses)
    foreach ($p in $ui) { Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue }
    Write-Host "Stopped $($ui.Count) UI process(es)."
    & powershell -NoProfile -ExecutionPolicy Bypass -File $LiveScript -Stop
    exit 0
}

Write-Host "=== TwinGuard AI ===" -ForegroundColor Cyan

# 1. Prerequisites
if (-not (Test-Path (Join-Path $Root ".venv\Scripts\python.exe"))) { throw "Python virtualenv .venv not found in $Root." }
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) { throw "Node.js/npm not found. Install Node.js first." }
if (-not (Test-Path (Join-Path $Frontend "node_modules"))) {
    Write-Host "Installing UI dependencies (first run only)..."
    Push-Location $Frontend; try { npm ci } finally { Pop-Location }
}
if (-not (Test-Path (Join-Path $Frontend ".env.local"))) {
    Write-Host "Note: frontend\.env.local (Cesium ion token) is missing - the 3D map will not load Google 3D tiles." -ForegroundColor Yellow
}

# 2. AI service (flood engine, GPU worker, live forecasts) on :8000
if (Test-Url "http://127.0.0.1:8000/health") {
    Write-Host "AI service already running on http://127.0.0.1:8000"
} else {
    & powershell -NoProfile -ExecutionPolicy Bypass -File $LiveScript -Background
    if (-not (Wait-Url "http://127.0.0.1:8000/health" 120 "AI service")) {
        throw "AI service did not start. See the newest log in $LogDir"
    }
}

# 3. UI dev server on :$UiPort
if (Test-Url $UiUrl) {
    Write-Host "UI already running on $UiUrl"
} else {
    New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $uiLog = Join-Path $LogDir "ui-dev-$stamp.log"
    $npm = (Get-Command npm.cmd -ErrorAction SilentlyContinue).Source
    if (-not $npm) { $npm = (Get-Command npm).Source }
    $proc = Start-Process -FilePath $npm -ArgumentList "run", "dev", "--", "--port", "$UiPort", "--strictPort" `
        -WorkingDirectory $Frontend -WindowStyle Hidden -RedirectStandardOutput $uiLog -RedirectStandardError "$uiLog.err" -PassThru
    Write-Host "UI dev server starting (PID $($proc.Id)); log: $uiLog"
    if (-not (Wait-Url $UiUrl 90 "UI")) { throw "UI did not start. See $uiLog(.err)" }
}

# 4. Browser
if (-not $NoBrowser) { Start-Process $UiUrl }

Write-Host ""
Write-Host "TwinGuard AI is running:" -ForegroundColor Green
Write-Host "  UI          $UiUrl"
Write-Host "  AI service  http://127.0.0.1:8000  (live forecast every 3 h, GPU when available)"
Write-Host "Stop everything with: stop_twinguard.bat  (or start_twinguard.ps1 -Stop)"
