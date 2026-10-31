[CmdletBinding()]
param(
    [string]$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
)

$ErrorActionPreference = 'Stop'
$resolvedRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path
$statePath = Join-Path $resolvedRoot 'docs\master\STATE.json'
$gateStatus = 'unknown'

try {
    $state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json -ErrorAction Stop
    $g0Entries = @($state.gates | Where-Object { $_.id -ceq 'G0' })
    if ($g0Entries.Count -eq 1 -and $g0Entries[0].status -cin @('ready', 'not_ready')) {
        $gateStatus = [string]$g0Entries[0].status
    }
}
catch {
    $gateStatus = 'unknown'
}

$previousStatus = $env:TWINGUARD_G0_STATUS
$composePath = Join-Path $resolvedRoot 'docker-compose.b11.yml'
try {
    $env:TWINGUARD_G0_STATUS = $gateStatus
    Push-Location -LiteralPath $resolvedRoot
    try {
        & docker compose -p twinguard-b11 -f $composePath build --pull=false frontend
        if ($LASTEXITCODE -ne 0) {
            throw "Static frontend package build failed with exit code $LASTEXITCODE."
        }
    }
    finally {
        Pop-Location
    }
}
finally {
    if ($null -eq $previousStatus) {
        Remove-Item Env:\TWINGUARD_G0_STATUS -ErrorAction SilentlyContinue
    }
    else {
        $env:TWINGUARD_G0_STATUS = $previousStatus
    }
}

Write-Output "Packaged static frontend with authoritative G0 status: $gateStatus"
