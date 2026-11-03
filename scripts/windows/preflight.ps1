[CmdletBinding()]
param(
    [ValidateSet('native','docker')]
    [string]$Runtime = 'native'
)

$ErrorActionPreference = 'Stop'

function Test-Command([string]$Name) {
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$ComposeFile = Join-Path $RepoRoot 'docker-compose.yml'

$checks = [ordered]@{}
$checks['Windows'] = $IsWindows -or $env:OS -eq 'Windows_NT'
$checks['PowerShell7'] = $PSVersionTable.PSVersion.Major -ge 7
$checks['Git'] = Test-Command 'git'
$checks['CodexHome'] = Test-Path (Join-Path $env:USERPROFILE '.codex')
$checks['CodexConfig'] = Test-Path (Join-Path $env:USERPROFILE '.codex\config.toml')

try {
    $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 4000)
    $listener.Start()
    $listener.Stop()
    $checks['Port4000Available'] = $true
}
catch {
    $checks['Port4000Available'] = $false
}

if (-not $checks['Port4000Available']) {
    try {
        Invoke-RestMethod -Method Get -Uri 'http://127.0.0.1:4000/health/liveliness' -TimeoutSec 2 | Out-Null
        $checks['Port4000Available'] = $true
    }
    catch {
        # A foreign listener on the router port remains a hard failure.
    }
}

if ($Runtime -eq 'docker') {
    $checks['DockerCLI'] = Test-Command 'docker'
    if ($checks['DockerCLI']) {
        try {
            docker version --format '{{.Server.Version}}' | Out-Null
            $checks['DockerDaemon'] = $true
        }
        catch {
            $checks['DockerDaemon'] = $false
        }
        try {
            docker compose version | Out-Null
            $checks['DockerCompose'] = $true
        }
        catch {
            $checks['DockerCompose'] = $false
        }
    }
    else {
        $checks['DockerDaemon'] = $false
        $checks['DockerCompose'] = $false
    }
}
else {
    $checks['uv'] = Test-Command 'uv'
    $checks['node'] = Test-Command 'node'
    $checks['psql'] = Test-Command 'psql'
    $checks['pg_isready'] = Test-Command 'pg_isready'
    $checks['createdb'] = Test-Command 'createdb'

    if ($checks['node']) {
        try {
            $nodeVersion = (& node --version).Trim().TrimStart('v')
            $nodeMajor = [int]($nodeVersion.Split('.')[0])
            $checks['Node24OrNewer'] = $nodeMajor -ge 24
        }
        catch {
            $checks['Node24OrNewer'] = $false
        }
    }
    else {
        $checks['Node24OrNewer'] = $false
    }
}

$checks.GetEnumerator() | ForEach-Object {
    [PSCustomObject]@{ Check = $_.Key; Pass = $_.Value }
} | Format-Table -AutoSize

if ($checks.Values -contains $false) { exit 1 }
exit 0
