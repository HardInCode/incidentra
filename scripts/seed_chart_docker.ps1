# Seed dashboard chart data into Docker Postgres (not Windows Postgres on :5432).
# Usage (from repo root):
#   .\scripts\seed_chart_docker.ps1
#   .\scripts\seed_chart_docker.ps1 -DryRun

param(
    [switch]$DryRun,
    [switch]$AppendLogs
)

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent

Push-Location $Root
try {
    $args = @("run", "--rm",
        "-e", "DATABASE_URL=postgresql+psycopg://smeguard:smeguard123@postgres:5432/smeguard_db",
        "-e", "PYTHONPATH=/app",
        "-v", "${Root}/backend:/app",
        "-v", "${Root}/scripts:/scripts",
        "backend",
        "python", "/scripts/seed_chart_demo.py", "--docker-internal")
    if ($DryRun) { $args += "--dry-run" }
    if ($AppendLogs) { $args += "--append-logs" }

    Write-Host "Seeding Docker DB (hostname postgres, not localhost:5432)..." -ForegroundColor Cyan
    docker compose @args
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Write-Host "Done. Refresh Dashboard at http://localhost:3000" -ForegroundColor Green
}
finally {
    Pop-Location
}
