$ErrorActionPreference = 'Stop'

Write-Host 'Starting local FastAPI server on http://127.0.0.1:8000'
$python = if (Test-Path '.venv/Scripts/python.exe') { '.venv/Scripts/python.exe' } else { 'python' }
& $python -m uvicorn agent.main:app --reload --host 127.0.0.1 --port 8000
