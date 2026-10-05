[CmdletBinding()]
param(
    [switch]$Yes
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $repoRoot "backend"

if (-not $Yes) {
    Write-Host ""
    Write-Host "WARNING: this removes the local DeCypher Docker volumes." -ForegroundColor Yellow
    Write-Host "It deletes local PostgreSQL, Neo4j, Prometheus and Grafana demo state."
    Write-Host "Do NOT use this if you need to preserve local investigation data."
    $answer = Read-Host "Type RESET to continue"
    if ($answer -ne "RESET") {
        Write-Host "Reset cancelled."
        exit 0
    }
}

Push-Location $backendDir
try {
    docker compose down -v
    if ($LASTEXITCODE -ne 0) {
        throw "docker compose down -v failed"
    }
}
finally {
    Pop-Location
}

Write-Host ""
Write-Host "Demo volumes removed. Starting a fresh deterministic demo..."
& (Join-Path $PSScriptRoot "start_demo.ps1")
