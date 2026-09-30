param(
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [string]$Username = "analyst",
    [string]$Password = "analystpassword",
    [string]$ActorId = "A00001"
)

$ErrorActionPreference = "Stop"

function Pass($message) { Write-Host "[PASS] $message" }
function Fail($message) { Write-Host "[FAIL] $message"; exit 1 }
function Assert-True($condition, $message) { if (-not $condition) { Fail $message }; Pass $message }

function Get-HttpStatus($method, $uri, $headers) {
    try {
        $response = Invoke-WebRequest -Method $method -Uri $uri -Headers $headers -UseBasicParsing -ErrorAction Stop
        return [int]$response.StatusCode
    } catch {
        if ($_.Exception.Response) { return [int]$_.Exception.Response.StatusCode.value__ }
        throw
    }
}

Write-Host "DeCypher runtime smoke test"
Write-Host "Base URL: $BaseUrl"
Write-Host ""

$health = Invoke-RestMethod -Method Get -Uri "$BaseUrl/health"
Assert-True ($health.status -eq "healthy") "API health is healthy"
Assert-True ($health.checks.postgres -eq "healthy") "PostgreSQL health is healthy"
Assert-True ($health.checks.neo4j -eq "healthy") "Neo4j health is healthy"
Assert-True ($health.checks.redis -eq "healthy") "Redis health is healthy"
Assert-True ($health.checks.nlp -eq "validated_model") "NLP engine is validated_model"

$loginBody = @{ username = $Username; password = $Password }
$login = Invoke-RestMethod -Method Post -Uri "$BaseUrl/auth/token" -ContentType "application/x-www-form-urlencoded" -Body $loginBody
Assert-True (-not [string]::IsNullOrWhiteSpace($login.access_token)) "Analyst login returns an access token"
$headers = @{ Authorization = "Bearer $($login.access_token)" }

$actors = Invoke-RestMethod -Method Get -Uri "$BaseUrl/actors?limit=3" -Headers $headers
Assert-True ($actors.Count -ge 1 -and $actors.Count -le 3) "Protected actor listing returns a bounded result set"

$actor = Invoke-RestMethod -Method Get -Uri "$BaseUrl/actors/$ActorId" -Headers $headers
Assert-True ($actor.actor_id -eq $ActorId) "Actor detail returns $ActorId"

$evidence = Invoke-RestMethod -Method Get -Uri "$BaseUrl/actors/$ActorId/evidence" -Headers $headers
Assert-True ($evidence.Count -ge 1) "Actor evidence endpoint returns evidence"

$sampleTimestamp = [DateTimeOffset]::Parse([string]$evidence[0].timestamp).ToUniversalTime()
$start = [uri]::EscapeDataString($sampleTimestamp.AddMinutes(-1).ToString("o"))
$end = [uri]::EscapeDataString($sampleTimestamp.AddMinutes(1).ToString("o"))
$filtered = Invoke-RestMethod -Method Get -Uri "$BaseUrl/actors/$ActorId/evidence?start=$start&end=$end" -Headers $headers
Assert-True ($filtered.Count -ge 1 -and $filtered.Count -le $evidence.Count) "Evidence date-range filter works"
$reversedStatus = Get-HttpStatus "Get" "$BaseUrl/actors/$ActorId/evidence?start=$end&end=$start" $headers
Assert-True ($reversedStatus -eq 400) "Reversed evidence date range is rejected"

$graph = Invoke-RestMethod -Method Get -Uri "$BaseUrl/actors/$ActorId/graph" -Headers $headers
Assert-True ($graph.nodes.Count -ge 1) "Actor graph returns nodes"
Assert-True ($graph.links.Count -ge 1) "Actor graph returns relationships"

$exportJsonStatus = Get-HttpStatus "Get" "$BaseUrl/export/actor/$ActorId/json" $headers
Assert-True ($exportJsonStatus -eq 200) "Actor JSON export responds 200"
$exportCsvStatus = Get-HttpStatus "Get" "$BaseUrl/export/actor/$ActorId/csv" $headers
Assert-True ($exportCsvStatus -eq 200) "Actor CSV export responds 200"
$exportReportStatus = Get-HttpStatus "Get" "$BaseUrl/export/actor/$ActorId/report" $headers
Assert-True ($exportReportStatus -eq 200) "Actor PDF report export responds 200"

$repoRoot = Split-Path -Parent $PSScriptRoot
$composeFile = Join-Path $repoRoot "backend\docker-compose.yml"
$postgresState = docker inspect -f "{{.State.Status}}" threat_postgres
$neo4jState = docker inspect -f "{{.State.Status}}" threat_neo4j
$redisState = docker inspect -f "{{.State.Status}}" threat_redis
Assert-True ($postgresState -eq "running") "PostgreSQL container is running"
Assert-True ($neo4jState -eq "running") "Neo4j container is running"
Assert-True ($redisState -eq "running") "Redis container is running"
$workerState = docker inspect -f "{{.State.Status}}" threat_celery_worker
$beatState = docker inspect -f "{{.State.Status}}" threat_celery_beat
Assert-True ($workerState -eq "running") "Celery worker container is running"
Assert-True ($beatState -eq "running") "Celery Beat container is running"

$nlpResult = docker compose -f $composeFile exec -T celery_worker python -c "from app.services.nlp_service import nlp_service; print(nlp_service.engine_status); print(nlp_service.engine is not None)"
$nlpLines = @($nlpResult | Where-Object { $_ -and $_.Trim() })
Assert-True ($nlpLines -contains "validated_model") "Celery worker loads the validated NLP model"
Assert-True ($nlpLines -contains "True") "Celery worker has a loaded NLP engine"

$workerLog = docker compose -f $composeFile logs --tail=80 celery_worker
Assert-True ($workerLog -match "Connected to redis://redis:6379/0") "Celery worker is connected to Redis"
Assert-True ($workerLog -match "ready\.") "Celery worker reached ready state"
Assert-True ($workerLog -match "dispatch_due_scans.*succeeded") "Celery worker successfully executed dispatch_due_scans"

Write-Host ""
Pass "All runtime smoke checks passed."