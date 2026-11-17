$ErrorActionPreference = 'Stop'
Push-Location (Split-Path -Parent $PSScriptRoot)
try {
    if (-not (Test-Path .env)) { throw 'Run ./scripts/setup.ps1 first.' }
    docker compose -f compose.yaml -f compose.dev.yaml up --build --detach --wait --wait-timeout 240
    if ($LASTEXITCODE -ne 0) { throw 'Startup failed. Inspect: docker compose -f compose.yaml -f compose.dev.yaml logs --tail 60' }
    Write-Host 'Open the loopback URL listed by: docker compose -f compose.yaml -f compose.dev.yaml port nginx 80'
} finally { Pop-Location }
