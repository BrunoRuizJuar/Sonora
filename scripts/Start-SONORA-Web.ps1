# Same origin, one serving worker. Never serve the repository root.
. (Join-Path $PSScriptRoot 'Enter-SONORA.ps1')
& .venv\Scripts\python.exe -m uvicorn sonora_api.main:app --host 127.0.0.1 --port 8010 --workers 1
