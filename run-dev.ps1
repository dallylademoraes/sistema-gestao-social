$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendEnv = Join-Path $root "backend/.env"
$backendEnvExample = Join-Path $root "backend/.env.example"

if (-not (Test-Path $backendEnv)) {
  if (Test-Path $backendEnvExample) {
    Copy-Item $backendEnvExample $backendEnv
    Write-Host "Criado backend/.env a partir de .env.example (edite se precisar de PostgreSQL)." -ForegroundColor Yellow
  } else {
    Write-Host "Aviso: backend/.env nao existe e .env.example nao foi encontrado." -ForegroundColor Yellow
  }
}

Write-Host "Subindo backend e frontend..." -ForegroundColor Cyan

Start-Process pwsh -ArgumentList @(
  "-NoExit",
  "-Command",
  "Set-Location '$root/backend'; ./venv/Scripts/python.exe -m uvicorn app.main:app --reload"
)

Start-Process pwsh -ArgumentList @(
  "-NoExit",
  "-Command",
  "Set-Location '$root/frontend'; npm run dev"
)

Write-Host "Backend: http://127.0.0.1:8000/docs" -ForegroundColor Green
Write-Host "Frontend: http://localhost:5173" -ForegroundColor Green
