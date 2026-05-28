# Reset Incidentra data via Docker Compose (bukan Windows Postgres di :5432).
#
# Usage (dari repo root):
#   .\scripts\reset_incidentra_docker.ps1
#   .\scripts\reset_incidentra_docker.ps1 -ClearLogs
#   .\scripts\reset_incidentra_docker.ps1 -ResetAll
#   .\scripts\reset_incidentra_docker.ps1 -ClearLogs -ResetAll
#
# Flags:
#   -ClearLogs  : Kosongkan vuln-web/logs/access.log di dalam volume
#   -ResetAll   : Juga hapus app_settings (API keys, SMTP, Telegram hilang!)

param(
    [switch]$ClearLogs,
    [switch]$ResetAll
)

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent

Push-Location $Root
try {
    $runArgs = @(
        "run", "--rm",
        "-e", "DATABASE_URL=postgresql+psycopg://incidentra:incidentra123@postgres:5432/incidentra_db",
        "-e", "REDIS_URL=redis://redis:6379/0",
        "-e", "PYTHONPATH=/app",
        "-v", "${Root}/backend:/app",
        "-v", "${Root}/scripts:/scripts",
        "-v", "vuln_logs:/vuln-web/logs",
        "backend",
        "python", "/scripts/reset_incidentra.py", "--docker-internal"
    )

    if ($ClearLogs) { $runArgs += "--clear-logs" }
    if ($ResetAll)  { $runArgs += "--reset-all" }

    if ($ResetAll) {
        Write-Host ""
        Write-Host "⚠️  MODE --reset-all aktif: API keys, SMTP, Telegram config akan dihapus!" -ForegroundColor Yellow
        Write-Host ""
    }

    Write-Host "Mereset Incidentra via Docker (hostname postgres & redis, bukan localhost)..." -ForegroundColor Cyan
    docker compose @runArgs
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host ""
    Write-Host "✅ Reset selesai. Restart backend jika perlu:" -ForegroundColor Green
    Write-Host "   docker compose restart backend" -ForegroundColor Gray
}
finally {
    Pop-Location
}
