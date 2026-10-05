[CmdletBinding()]
param(
    [switch]$NoFrontend
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $repoRoot "backend"
$frontendDir = Join-Path $repoRoot "frontend"
$envPath = Join-Path $backendDir ".env"
$envExamplePath = Join-Path $backendDir ".env.example"

function Fail([string]$Message) {
    Write-Host ""
    Write-Host "[ERROR] $Message" -ForegroundColor Red
    exit 1
}

function Info([string]$Message) { Write-Host "[*] $Message" }
function Pass([string]$Message) { Write-Host "[OK] $Message" -ForegroundColor Green }

function New-HexSecret([int]$Bytes = 24) {
    $buffer = New-Object byte[] $Bytes
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($buffer) } finally { $rng.Dispose() }
    return [Convert]::ToHexString($buffer)
}

function Get-EnvValue([string]$Text, [string]$Name) {
    $pattern = "(?m)^" + [regex]::Escape($Name) + "=(.*)$"
    $match = [regex]::Match($Text, $pattern)
    if (-not $match.Success) { return $null }
    return $match.Groups[1].Value.Trim()
}

function Set-EnvValue([string]$Text, [string]$Name, [string]$Value) {
    $pattern = "(?m)^" + [regex]::Escape($Name) + "=.*$"
    $replacement = $Name + "=" + $Value
    if ([regex]::IsMatch($Text, $pattern)) {
        return [regex]::Replace($Text, $pattern, $replacement)
    }
    if (-not $Text.EndsWith([Environment]::NewLine)) {
        $Text += [Environment]::NewLine
    }
    return $Text + $replacement + [Environment]::NewLine
}

function Set-EnvPlaceholder([string]$Text, [string]$Name, [string]$Value, [string[]]$Placeholders) {
    $current = Get-EnvValue $Text $Name
    if ([string]::IsNullOrWhiteSpace($current) -or $Placeholders -contains $current) {
        return Set-EnvValue $Text $Name $Value
    }
    return $Text
}

Info "DeCypher local demo bootstrap"
Info "Repository: $repoRoot"

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Fail "Docker is not installed or is not available on PATH. Install Docker Desktop first."
}

try {
    $null = docker info --format "{{.ServerVersion}}" 2>$null
    if ($LASTEXITCODE -ne 0) { throw "Docker daemon unavailable" }
}
catch {
    Fail "Docker Desktop is installed, but the Docker engine is not running. Start Docker Desktop and wait until it is ready, then run this script again."
}

try {
    $null = docker compose version 2>$null
    if ($LASTEXITCODE -ne 0) { throw "Compose unavailable" }
}
catch {
    Fail "Docker Compose is not available through the Docker CLI."
}
Pass "Docker and Docker Compose are available."

$nodeCmd = Get-Command node -ErrorAction SilentlyContinue
$npmCmd = Get-Command npm -ErrorAction SilentlyContinue
if (-not $nodeCmd -or -not $npmCmd) {
    Fail "Node.js and npm are required for the frontend. Install Node.js 20.19+ or 22.12+."
}

$nodeVersionText = (& node --version).TrimStart("v")
try { $nodeVersion = [version]$nodeVersionText } catch { Fail "Could not determine the installed Node.js version." }
if ($nodeVersion -lt [version]"20.19.0") {
    Fail "Node.js $nodeVersionText is too old. Install Node.js 20.19+ or 22.12+."
}
Pass "Node.js $nodeVersionText and npm are available."

if (-not (Test-Path $envExamplePath)) {
    Fail "Missing backend/.env.example. The repository checkout appears incomplete."
}

$postgresPassword = New-HexSecret 24
$neo4jPassword = New-HexSecret 24
$grafanaPassword = New-HexSecret 24
$secretKey = New-HexSecret 32
$adminPassword = New-HexSecret 12
$analystPassword = New-HexSecret 12
$scannerPassword = New-HexSecret 12

if (Test-Path $envPath) {
    $envText = Get-Content -Raw -Path $envPath
    $createdEnv = $false
}
else {
    $envText = Get-Content -Raw -Path $envExamplePath
    $createdEnv = $true
}

$envText = Set-EnvPlaceholder $envText "POSTGRES_PASSWORD" $postgresPassword @("change-this-in-local-env")
$envText = Set-EnvPlaceholder $envText "NEO4J_PASSWORD" $neo4jPassword @("change-this-neo4j-password", "change-this-in-local-env")
$envText = Set-EnvPlaceholder $envText "GRAFANA_ADMIN_PASSWORD" $grafanaPassword @("change-this-in-local-env")
$envText = Set-EnvPlaceholder $envText "SECRET_KEY" $secretKey @("replace-with-a-unique-random-secret")
$envText = Set-EnvPlaceholder $envText "ADMIN_PASSWORD" $adminPassword @("replace-with-a-strong-admin-password")
$envText = Set-EnvPlaceholder $envText "ANALYST_PASSWORD" $analystPassword @("replace-with-a-strong-investigator-password")
$envText = Set-EnvPlaceholder $envText "SCANNER_SERVICE_PASSWORD" $scannerPassword @("replace-with-a-strong-service-password")

$databaseValue = Get-EnvValue $envText "DATABASE_URL"
if ([string]::IsNullOrWhiteSpace($databaseValue) -or $databaseValue -match "change-this-in-local-env") {
    $envText = Set-EnvValue $envText "DATABASE_URL" "postgresql+psycopg2://postgres:$postgresPassword@127.0.0.1:5433/threat_intel"
}

$envText = Set-EnvValue $envText "DEMO_MODE" "true"
$envText = Set-EnvValue $envText "DEMO_DATASET_VERSION" "2026-10-05-v1"
$envText = Set-EnvValue $envText "DEMO_REFERENCE_DATE" "2026-10-05"
$envText = Set-EnvValue $envText "AUTOSCAN_ENABLED" "false"
$envText = Set-EnvValue $envText "COLLECTION_ENABLED" "false"

# Re-read the final values. Existing real credentials are preserved and are
# the values used for derived settings such as DATABASE_URL and the console output.
$postgresPassword = Get-EnvValue $envText "POSTGRES_PASSWORD"
$neo4jPassword = Get-EnvValue $envText "NEO4J_PASSWORD"
$grafanaPassword = Get-EnvValue $envText "GRAFANA_ADMIN_PASSWORD"
$secretKey = Get-EnvValue $envText "SECRET_KEY"
$adminPassword = Get-EnvValue $envText "ADMIN_PASSWORD"
$analystPassword = Get-EnvValue $envText "ANALYST_PASSWORD"
$scannerPassword = Get-EnvValue $envText "SCANNER_SERVICE_PASSWORD"

if ([string]::IsNullOrWhiteSpace($postgresPassword) -or
    [string]::IsNullOrWhiteSpace($neo4jPassword) -or
    [string]::IsNullOrWhiteSpace($grafanaPassword) -or
    [string]::IsNullOrWhiteSpace($secretKey) -or
    [string]::IsNullOrWhiteSpace($adminPassword) -or
    [string]::IsNullOrWhiteSpace($analystPassword) -or
    [string]::IsNullOrWhiteSpace($scannerPassword)) {
    Fail "backend/.env is missing one or more required credentials."
}

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($envPath, $envText, $utf8NoBom)

if ($createdEnv) {
    Pass "Created backend/.env with local-only generated credentials."
}
else {
    Pass "Existing backend/.env preserved; only known template placeholders were repaired."
}

Info "Starting backend services..."
Push-Location $backendDir
try {
    & docker compose up -d --build
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        & docker compose ps
        Fail "Docker Compose failed to start."
    }

    $deadline = (Get-Date).AddMinutes(5)
    $healthy = $false

    while ((Get-Date) -lt $deadline) {
        try {
            $health = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -Method Get -TimeoutSec 5
            if ($health.status -eq "healthy") {
                $healthy = $true
                break
            }
        } catch {}
        Start-Sleep -Seconds 5
    }

    if (-not $healthy) {
        Write-Host ""
        & docker compose ps
        Write-Host ""
        & docker compose logs --tail=100 api
        Fail "API did not become dependency-healthy within 5 minutes."
    }

    Pass "PostgreSQL, Redis, Neo4j and API readiness checks passed."
}
finally {
    Pop-Location
}

if (-not $NoFrontend) {
    Info "Preparing frontend..."
    Push-Location $frontendDir
    try {
        if (-not (Test-Path (Join-Path $frontendDir "node_modules"))) {
            Info "Installing frontend dependencies with npm ci..."
            & npm ci
            if ($LASTEXITCODE -ne 0) {
                Fail "npm ci failed."
            }
        }
        else {
            Pass "Frontend dependencies already installed."
        }

        Write-Host ""
        Write-Host "========================================" -ForegroundColor Cyan
        Write-Host " DeCypher Demo Ready" -ForegroundColor Cyan
        Write-Host "========================================" -ForegroundColor Cyan
        Write-Host "Frontend : http://localhost:5173"
        Write-Host "API      : http://127.0.0.1:8000"
        Write-Host "API docs : http://127.0.0.1:8000/docs"
        Write-Host ""
        Write-Host "Login credentials"
        Write-Host "  admin   : $adminPassword"
        Write-Host "  analyst : $analystPassword"
        Write-Host ""
        Write-Host "Generated backend/.env is local-only and must not be committed." -ForegroundColor Yellow
        Write-Host "Press Ctrl+C to stop Vite. Docker services remain running."
        Write-Host "========================================" -ForegroundColor Cyan
        Write-Host ""

        & npm run dev -- --host 127.0.0.1
    }
    finally {
        Pop-Location
    }
}
else {
    Write-Host ""
    Write-Host "DeCypher backend is ready."
    Write-Host "API: http://127.0.0.1:8000"
    Write-Host "API docs: http://127.0.0.1:8000/docs"
    Write-Host "admin: $adminPassword"
    Write-Host "analyst: $analystPassword"
}
