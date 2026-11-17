# Purpose: initialize and start the full local Docker application, then smoke test.
# Input: Docker Linux daemon, root .env or .env.example, local Python interpreter.
# Output: verified service URL; nonzero exit on failure; never prints credentials.
$ErrorActionPreference = 'Stop'
Push-Location (Split-Path -Parent $PSScriptRoot)
try {
    & ./scripts/setup.ps1
    & ./scripts/dev.ps1
    if (Test-Path ./.venv/Scripts/python.exe) {
        & ./.venv/Scripts/python.exe scripts/smoke.py
    } elseif (Get-Command python -ErrorAction SilentlyContinue) {
        python scripts/smoke.py
    } else {
        py -3 scripts/smoke.py
    }
    if ($LASTEXITCODE -ne 0) { throw 'Services started but the end-to-end check failed. Inspect api/worker logs.' }
    $address = docker compose -f compose.yaml -f compose.dev.yaml port nginx 80
    if ($LASTEXITCODE -ne 0) { throw 'Cannot determine the local HTTP address.' }
    Write-Host "Open http://$address"
    Write-Host 'Paste DEMO_API_TOKEN from your local .env into the page. Do not share that file.'
    Write-Host 'Closing this window keeps containers running. Stop with: docker compose -f compose.yaml -f compose.dev.yaml down'
} catch {
    Write-Host 'Local startup failed. Check the error below and rerun start.cmd.' -ForegroundColor Red
    Write-Error $_
    exit 1
} finally { Pop-Location }
