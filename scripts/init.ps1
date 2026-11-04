$ErrorActionPreference = "Stop"

$ROOT = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ROOT

Write-Host "=== LifeHub Init ==="

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"

    Write-Host ""
    Write-Host "  Created .env from .env.example."
    Write-Host "  -> Edit .env and set POSTGRES_PASSWORD, SECRET_KEY, ADMIN_PASSWORD."
    Write-Host "  -> Then run this script again."
    Write-Host ""

    exit 0
}

Write-Host "Building and starting services..."
docker compose up -d --build

# Legge le porte dal .env, con fallback ai valori predefiniti
$frontendPort = "3000"
$backendPort = "8000"

foreach ($line in Get-Content ".env") {
    if ($line -match '^\s*FRONTEND_PORT\s*=\s*(.+)\s*$') {
        $frontendPort = $Matches[1].Trim().Trim('"').Trim("'")
    }

    if ($line -match '^\s*BACKEND_PORT\s*=\s*(.+)\s*$') {
        $backendPort = $Matches[1].Trim().Trim('"').Trim("'")
    }
}

Write-Host ""
Write-Host "  LifeHub is starting up."
Write-Host ""
Write-Host "  Frontend : http://localhost:$frontendPort"
Write-Host "  Backend  : http://localhost:$backendPort"
Write-Host "  API docs : http://localhost:$backendPort/api/docs"
Write-Host ""
Write-Host "  Logs: docker compose logs -f"
