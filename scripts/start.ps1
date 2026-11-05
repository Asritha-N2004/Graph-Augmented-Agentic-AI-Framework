param([int]$ApiPort=8010,[int]$DashboardPort=3000)
$ErrorActionPreference='Stop'
$projectRoot=Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
if (Get-NetTCPConnection -LocalPort $ApiPort,$DashboardPort -State Listen -ErrorAction SilentlyContinue) { throw 'A selected port is occupied. Stop the existing preview or choose different -ApiPort / -DashboardPort values.' }
if (-not (Test-Path 'backend/artifacts/models/manifest.json')) { throw 'Train first: python -m backend.pipeline --epochs 40 --regenerate' }
if (-not (Test-Path 'frontend/node_modules/next/dist/bin/next')) { throw 'Install frontend dependencies first. See README.md.' }
$pythonPath=if (Test-Path '.venv/Scripts/python.exe') { (Resolve-Path '.venv/Scripts/python.exe').Path } else { (Get-Command python).Source }
$nodePath=(Get-Command node).Source
if (Test-Path '.deps') { $env:PYTHONPATH=Join-Path $projectRoot '.deps' }
$env:CORS_ORIGINS="http://localhost:$DashboardPort,http://127.0.0.1:$DashboardPort"
$env:NEXT_PUBLIC_API_URL="http://localhost:$ApiPort"
$backend=Start-Process -FilePath $pythonPath -ArgumentList @('-m','uvicorn','backend.app.main:app','--host','127.0.0.1','--port',"$ApiPort") -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $projectRoot 'backend-api.log') -RedirectStandardError (Join-Path $projectRoot 'backend-api-error.log')
$frontend=Start-Process -FilePath $nodePath -ArgumentList @('node_modules/next/dist/bin/next','dev','--webpack','--hostname','127.0.0.1','--port',"$DashboardPort") -WorkingDirectory (Join-Path $projectRoot 'frontend') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $projectRoot 'dashboard.log') -RedirectStandardError (Join-Path $projectRoot 'dashboard-error.log')
Write-Host "CIRP dashboard: http://localhost:$DashboardPort"
Write-Host "CIRP API docs: http://localhost:$ApiPort/docs"
Write-Host "Started process IDs: API=$($backend.Id), dashboard=$($frontend.Id). Logs are in the project root."
