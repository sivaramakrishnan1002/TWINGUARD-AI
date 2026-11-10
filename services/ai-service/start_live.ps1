<#
.SYNOPSIS
  Start the TwinGuard AI service (C4 v3 /v3) with live forecast mode and the persistent GPU worker, outside any
  Claude session, so it keeps running when sessions end.

.DESCRIPTION
  Serves http://127.0.0.1:<Port> (default 8000), the target of the UI's /api/ai proxy.
  Settings:
    - TWINGUARD_V3_LIVE=1 (3 h live cycle, start-up catch-up)
    - TWINGUARD_V3_DEVICE=auto (CUDA when available, else CPU)
    - TWINGUARD_V3_WORKER=auto (persistent GPU worker when CUDA resolves)
  Logs go to data\features\v3\logs\ai-service-<timestamp>.log (git-ignored).

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File services\ai-service\start_live.ps1             # foreground; Ctrl+C stops
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File services\ai-service\start_live.ps1 -Background # detached; survives closing the terminal
.EXAMPLE
  powershell -ExecutionPolicy Bypass -File services\ai-service\start_live.ps1 -Stop       # stop a running instance
#>
param(
    [switch]$Background,
    [switch]$Stop,
    [int]$Port = 8000,
    [switch]$NoLive
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$Launcher = "services\ai-service\run_local.py"
$LogDir = Join-Path $Root "data\features\v3\logs"

function Get-ServiceProcesses {
    Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
        Where-Object { $_.CommandLine -match 'run_local\.py|app\.v3\.worker --serve' }
}

if ($Stop) {
    $procs = @(Get-ServiceProcesses)
    if (-not $procs) { Write-Host "No TwinGuard AI service process found."; exit 0 }
    foreach ($p in $procs) { Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue }
    Write-Host "Stopped $($procs.Count) TwinGuard AI service process(es)."
    exit 0
}

if (-not (Test-Path $Python)) { throw "Python virtualenv not found at $Python (create .venv first)." }

try {
    $null = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$Port/health" -TimeoutSec 2
    Write-Host "An AI service already answers on http://127.0.0.1:$Port - not starting a second one (use -Stop first)."
    exit 0
} catch { }

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$log = Join-Path $LogDir "ai-service-$stamp.log"

$env:TWINGUARD_AI_PORT = "$Port"
$env:TWINGUARD_V3_LIVE = $(if ($NoLive) { "0" } else { "1" })
$env:TWINGUARD_V3_DEVICE = "auto"
$env:TWINGUARD_V3_WORKER = "auto"
$env:TWINGUARD_LIVE_SCHEDULE_MIN = "0"
$env:PYTHONUNBUFFERED = "1"

if ($Background) {
    $proc = Start-Process -FilePath $Python -ArgumentList $Launcher -WorkingDirectory $Root -WindowStyle Hidden `
        -RedirectStandardOutput $log -RedirectStandardError "$log.err" -PassThru
    Write-Host "TwinGuard AI service started in the background (PID $($proc.Id)) on http://127.0.0.1:$Port"
    Write-Host "Logs: $log (+ .err). Stop with: powershell -ExecutionPolicy Bypass -File services\ai-service\start_live.ps1 -Stop"
} else {
    Write-Host "TwinGuard AI service on http://127.0.0.1:$Port (live mode $($env:TWINGUARD_V3_LIVE)); logging to $log. Ctrl+C stops."
    Push-Location $Root
    try { & $Python $Launcher 2>&1 | Tee-Object -FilePath $log } finally { Pop-Location }
}
