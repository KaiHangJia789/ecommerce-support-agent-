$ErrorActionPreference = 'Stop'
$previousEnvironment = $env:UV_PROJECT_ENVIRONMENT
Push-Location (Split-Path -Parent $PSScriptRoot)
try {
    $env:UV_PROJECT_ENVIRONMENT = Join-Path (Get-Location).Path '.venv'
    if (-not (Test-Path ./.venv/Scripts/python.exe)) { throw 'Run setup-env.cmd first to create the root Python 3.12 environment.' }
    # Scriptblocks: input none; output native exit status and check results.
    # In order: stdlib tests, backend lint/format/tests, frontend type check.
    $commands = @(
        { & ./.venv/Scripts/python.exe -m unittest discover -s tests },
        { uv run --project apps/backend --frozen --python-preference only-managed ruff check apps/backend },
        { uv run --project apps/backend --frozen --python-preference only-managed ruff format --check apps/backend },
        { uv run --project apps/backend --frozen --python-preference only-managed pytest apps/backend/tests },
        { pnpm --dir apps/web check }
    )
    foreach ($command in $commands) {
        & $command
        if ($LASTEXITCODE -ne 0) { throw 'A check failed; see preceding output.' }
    }
} finally {
    $env:UV_PROJECT_ENVIRONMENT = $previousEnvironment
    Pop-Location
}
