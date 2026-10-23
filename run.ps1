# Starts the Knowledge Converter locally: API on :8000, web app on :3000.
# First run creates the Python environment and installs npm packages.
$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$Python = Join-Path $Root "backend\.venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    Write-Host "Creating Python environment..."
    py -3 -m venv (Join-Path $Root "backend\.venv")
    & $Python -m pip install -r (Join-Path $Root "backend\requirements-dev.txt")
}
if (-not (Test-Path (Join-Path $Root "frontend\node_modules"))) {
    Write-Host "Installing frontend packages..."
    npm ci --prefix (Join-Path $Root "frontend")
}
if (-not (Test-Path (Join-Path $Root "frontend\.env.local"))) {
    Copy-Item (Join-Path $Root "frontend\.env.example") (Join-Path $Root "frontend\.env.local")
}

Write-Host ""
Write-Host "Mindjax Knowledge Converter"
Write-Host "  API  http://127.0.0.1:8000"
Write-Host "  Web  http://localhost:3000"
Write-Host "Press Ctrl+C to stop."
Write-Host ""

$api = Start-Process -FilePath $Python -ArgumentList "-m", "uvicorn", "api.main:app", "--app-dir", "backend", "--host", "127.0.0.1", "--port", "8000" -WorkingDirectory $Root -NoNewWindow -PassThru
try {
    npm run dev --prefix (Join-Path $Root "frontend")
}
finally {
    if ($api -and -not $api.HasExited) { Stop-Process -Id $api.Id -Force }
}
