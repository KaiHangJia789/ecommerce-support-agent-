$ErrorActionPreference = 'Stop'
Push-Location (Split-Path -Parent $PSScriptRoot)
try {
    $dockerOs = docker info --format '{{.OSType}}'
    if ($LASTEXITCODE -ne 0 -or $dockerOs -ne 'linux') { throw 'Start Docker Desktop with Linux containers first.' }
    if (Test-Path ./.venv/Scripts/python.exe) {
        & ./.venv/Scripts/python.exe scripts/bootstrap.py
    } elseif (Get-Command python -ErrorAction SilentlyContinue) {
        python scripts/bootstrap.py
    } elseif (Get-Command py -ErrorAction SilentlyContinue) {
        py -3 scripts/bootstrap.py
    } else {
        throw 'Install Python 3.10+ for setup; application Python runs inside Docker.'
    }
    if ($LASTEXITCODE -ne 0) { throw 'Configuration initialization failed; existing files preserved.' }
    docker compose -f compose.yaml -f compose.dev.yaml config --quiet
    if ($LASTEXITCODE -ne 0) { throw 'Compose configuration is invalid.' }
    Write-Host 'Ready. Start: ./scripts/dev.ps1'
} finally { Pop-Location }
