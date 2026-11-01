[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

function Test-Command([string]$Name) {
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

$checks = [ordered]@{}
$checks['Windows'] = $IsWindows -or $env:OS -eq 'Windows_NT'
$checks['DockerCLI'] = Test-Command 'docker'
$checks['Git'] = Test-Command 'git'
$checks['CodexHome'] = Test-Path (Join-Path $env:USERPROFILE '.codex')

if ($checks['DockerCLI']) {
    try {
        docker version --format '{{.Server.Version}}' | Out-Null
        $checks['DockerDaemon'] = $true
    } catch {
        $checks['DockerDaemon'] = $false
    }
} else {
    $checks['DockerDaemon'] = $false
}

$checks.GetEnumerator() | ForEach-Object {
    [PSCustomObject]@{ Check = $_.Key; Pass = $_.Value }
} | Format-Table -AutoSize

if ($checks.Values -contains $false) { exit 1 }
exit 0
