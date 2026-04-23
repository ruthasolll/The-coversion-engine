param(
  [string]$RepoUrl = 'https://github.com/sierra-research/tau-bench.git'
)

$ErrorActionPreference = 'Stop'
$target = Join-Path (Get-Location) 'eval/tau2/tau2-bench'

if (-not (Test-Path $target)) {
  git clone $RepoUrl $target
}

Write-Host "tau2 harness source available at: $target"
Write-Host "Run benchmark commands from that directory per upstream README."
