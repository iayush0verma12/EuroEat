# Starts the EuroEat backend (FastAPI :8000) and frontend (Vite :5173) on Windows.
# First run: installs dependencies. Requires Python 3.10+, Node 18+, and Ollama running locally.
$root = $PSScriptRoot

if (-not (Test-Path "$root\backend\.venv")) {
    Write-Host "Creating Python venv and installing backend deps..."
    py -3 -m venv "$root\backend\.venv"
    & "$root\backend\.venv\Scripts\python.exe" -m pip install -r "$root\backend\requirements.txt"
    & "$root\backend\.venv\Scripts\python.exe" -m playwright install chromium
}
if (-not (Test-Path "$root\frontend\node_modules")) {
    Write-Host "Installing frontend deps..."
    Push-Location "$root\frontend"; npm install; Pop-Location
}

Write-Host "Pulling Ollama models (skipped if present)..."
ollama pull llama3.2
ollama pull nomic-embed-text

Start-Process -FilePath "$root\backend\.venv\Scripts\python.exe" -ArgumentList "-m", "uvicorn", "app.main:app", "--port", "8000" -WorkingDirectory "$root\backend"
Start-Process -FilePath "npm.cmd" -ArgumentList "run", "dev" -WorkingDirectory "$root\frontend"
Write-Host ""
Write-Host "EuroEat is starting:  http://localhost:5173"
Write-Host "Login ID: traveller   Password: EuroEat@2026"
