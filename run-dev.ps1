$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path

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
