$ErrorActionPreference = 'Stop'
$python = if (Test-Path '.venv/Scripts/python.exe') { '.venv/Scripts/python.exe' } else { 'python' }

Write-Host 'Running import smoke test...'
& $python -c "import agent.main; import channels.email.resend_adapter; import channels.sms.africastalking_adapter; import enrichment.tenacious.jobs; print('import smoke passed')"
if ($LASTEXITCODE -ne 0) { throw 'Import smoke test failed.' }

Write-Host 'Running lightweight Playwright fetch test...'
& $python -c "from enrichment.tenacious.jobs import fetch_job_signals; r=fetch_job_signals('https://example.com'); print('playwright ok:', bool(r.get('title')))"
if ($LASTEXITCODE -ne 0) { throw 'Playwright smoke test failed.' }

Write-Host 'Smoke test complete.'
