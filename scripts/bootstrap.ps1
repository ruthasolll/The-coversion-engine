param(
  [switch]$SkipInstall,
  [switch]$SkipTau2Clone
)

$ErrorActionPreference = 'Stop'

Write-Host '== Conversion Engine bootstrap =='

if (-not (Test-Path '.env')) {
  Copy-Item '.env.example' '.env'
  Write-Host 'Created .env from .env.example (fill credentials manually).'
} else {
  Write-Host '.env already exists. Skipping copy.'
}

if (-not $SkipInstall) {
  Write-Host 'Creating local virtual environment (.venv) if needed.'
  if (-not (Test-Path '.venv/Scripts/python.exe')) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Failed to create virtual environment.' }
  }

  $venvPython = '.venv/Scripts/python.exe'

  Write-Host 'Ensuring pip is available in virtual environment.'
  & $venvPython -m ensurepip --upgrade
  if ($LASTEXITCODE -ne 0) { throw 'Failed to bootstrap pip in virtual environment.' }

  Write-Host 'Installing Python dependencies into local virtual environment.'
  & $venvPython -m pip install -r requirements.txt
  if ($LASTEXITCODE -ne 0) { throw 'Dependency install failed.' }

  Write-Host 'Installing Playwright Chromium browser binary.'
  & $venvPython -m playwright install chromium
  if ($LASTEXITCODE -ne 0) { throw 'Playwright install failed.' }
} else {
  Write-Host 'Skipping dependency install by request.'
}

if (-not $SkipTau2Clone) {
  $tauDir = Join-Path (Get-Location) 'eval/tau2/tau2-bench'
  if (Test-Path $tauDir) {
    Write-Host 'tau2-bench already present. Skipping clone.'
  } else {
    Write-Host 'Cloning tau2-bench as standalone repository into eval/tau2/tau2-bench.'
    git clone https://github.com/sierra-research/tau-bench.git $tauDir
    if ($LASTEXITCODE -ne 0) { throw 'tau2-bench clone failed.' }
  }
} else {
  Write-Host 'Skipping tau2-bench clone by request.'
}

Write-Host 'Bootstrap completed.'
