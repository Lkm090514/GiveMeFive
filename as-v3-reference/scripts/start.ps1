$ErrorActionPreference = 'Stop'
$launcher = Join-Path $PSScriptRoot '../../Start-GiveMeFive.cmd'
& $launcher @args
exit $LASTEXITCODE
