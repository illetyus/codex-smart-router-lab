[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

function Test-Command([string]$Name) {
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

$checks = [ordered]@{}
$checks['Windows'] = $IsWindows -or $env:OS -eq 'Windows_NT'
$checks['PowerShell7'] = $PSVersionTable.PSVersion.Major -ge 7
$checks['DockerCLI'] = Test-Command 'docker'
$checks['Git'] = Test-Command 'git'
$checks['CodexHome'] = Test-Path (Join-Path $env:USERPROFILE '.codex')
$checks['CodexConfig'] = Test-Path (Join-Path $env:USERPROFILE '.codex\config.toml')

try {
    $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 4000)
    $listener.Start()
    $listener.Stop()
    $checks['Port4000Available'] = $true
} catch {
    $checks['Port4000Available'] = $false
}

if ($checks['DockerCLI']) {
    try {
        docker version --format '{{.Server.Version}}' | Out-Null
        $checks['DockerDaemon'] = $true
    } catch {
        $checks['DockerDaemon'] = $false
    }
    try {
        docker compose version | Out-Null
        $checks['DockerCompose'] = $true
    } catch {
        $checks['DockerCompose'] = $false
    }
} else {
    $checks['DockerDaemon'] = $false
    $checks['DockerCompose'] = $false
}

$checks.GetEnumerator() | ForEach-Object {
    [PSCustomObject]@{ Check = $_.Key; Pass = $_.Value }
} | Format-Table -AutoSize

if ($checks.Values -contains $false) { exit 1 }
exit 0
