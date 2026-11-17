# Purpose: synchronize locked backend/dev dependencies into the root .venv.
# Input: installed uv, network/cache and backend pyproject.toml/uv.lock.
# Output: Python 3.12 .venv; restores caller's environment variable on exit.
$ErrorActionPreference = 'Stop'
$previousEnvironment = $env:UV_PROJECT_ENVIRONMENT
Push-Location (Split-Path -Parent $PSScriptRoot)
try {
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        throw 'Install uv first, then rerun setup-env.cmd. See README for developer prerequisites.'
    }
    $env:UV_PROJECT_ENVIRONMENT = Join-Path (Get-Location).Path '.venv'
    uv python install 3.12
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.12 installation failed.' }
    uv sync --project apps/backend --frozen --python 3.12 --python-preference only-managed --link-mode copy
    if ($LASTEXITCODE -ne 0) { throw 'Root virtual environment synchronization failed.' }
    & ./.venv/Scripts/python.exe -c "import sys; import support_agent; print('Python:', sys.version.split()[0]); print('Virtual environment:', sys.prefix)"
    if ($LASTEXITCODE -ne 0) { throw 'Root virtual environment verification failed.' }
    Write-Host 'Ready. Activate with: .\.venv\Scripts\Activate.ps1'
} finally {
    $env:UV_PROJECT_ENVIRONMENT = $previousEnvironment
    Pop-Location
}
