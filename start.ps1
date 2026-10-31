$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
& (Join-Path $PSScriptRoot 'run-app.bat')
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
