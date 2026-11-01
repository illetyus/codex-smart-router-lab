[CmdletBinding()]
param(
    [string]$CodexHome = (Join-Path $env:USERPROFILE '.codex')
)

$ErrorActionPreference = 'Stop'

function Test-Command([string]$Name) {
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

$checks = [ordered]@{}
$checks['Windows'] = $IsWindows -or $env:OS -eq 'Windows_NT'
$checks['DockerCLI'] = Test-Command 'docker'
$checks['Git'] = Test-Command 'git'
$checks['CodexHome'] = Test-Path -LiteralPath $CodexHome
$checks['CodexConfig'] = Test-Path -LiteralPath (Join-Path $CodexHome 'config.toml')

if ($checks['DockerCLI']) {
    & docker version --format '{{.Server.Version}}' *> $null
    $checks['DockerDaemon'] = $LASTEXITCODE -eq 0

    & docker compose version *> $null
    $checks['DockerCompose'] = $LASTEXITCODE -eq 0
}
else {
    $checks['DockerDaemon'] = $false
    $checks['DockerCompose'] = $false
}

$checks.GetEnumerator() | ForEach-Object {
    [PSCustomObject]@{ Check = $_.Key; Pass = $_.Value }
} | Format-Table -AutoSize

if ($checks.Values -contains $false) { exit 1 }
exit 0
