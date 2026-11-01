[CmdletBinding(SupportsShouldProcess)]
param(
    [ValidateSet('subscription','model-probe','autorouter')]
    [string]$Mode = 'subscription',
    [string]$CodexHome = (Join-Path $env:USERPROFILE '.codex')
)

$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$EnvFile = Join-Path $RepoRoot '.env'
$ComposeFile = Join-Path $RepoRoot 'docker-compose.yml'

& (Join-Path $PSScriptRoot 'preflight.ps1') -CodexHome $CodexHome
if ($LASTEXITCODE -ne 0) { throw 'Preflight failed.' }

function New-RandomHex([int]$Bytes = 32) {
    $buffer = New-Object byte[] $Bytes
    [System.Security.Cryptography.RandomNumberGenerator]::Fill($buffer)
    return -join ($buffer | ForEach-Object { $_.ToString('x2') })
}

if (-not (Test-Path $EnvFile)) {
    @(
        "LITELLM_MASTER_KEY=sk-$(New-RandomHex)",
        "LITELLM_SALT_KEY=sk-$(New-RandomHex)",
        "POSTGRES_PASSWORD=$(New-RandomHex 24)"
    ) | Set-Content -Path $EnvFile -Encoding utf8NoBOM
}

$config = switch ($Mode) {
    'subscription' { 'subscription.yaml' }
    'model-probe' { 'model-probe.yaml' }
    'autorouter' { 'autorouter.yaml' }
}
$env:CODEX_ROUTER_CONFIG = $config

if ($PSCmdlet.ShouldProcess('local Docker stack', "build and start LiteLLM in $Mode mode")) {
    docker compose -f $ComposeFile up -d --build --wait --wait-timeout 300
    if ($LASTEXITCODE -ne 0) { throw 'docker compose up did not reach healthy state.' }
}

Write-Host "Gateway is healthy in '$Mode' mode."

switch ($Mode) {
    'subscription' {
        Write-Host 'Next commands:'
        Write-Host '  pwsh -File .\scripts\windows\provision-codex-key.ps1 -Profile k2'
        Write-Host '  pwsh -File .\scripts\windows\configure-codex-provider.ps1'
        Write-Host '  pwsh -File .\scripts\windows\verify.ps1'
    }
    'model-probe' {
        Write-Host 'Next commands:'
        Write-Host '  pwsh -File .\scripts\windows\provision-codex-key.ps1 -Profile k3'
        Write-Host '  pwsh -File .\scripts\windows\verify.ps1'
        Write-Host 'Then follow docs/K3-MODEL-PROBE.md for direct model probes.'
    }
    'autorouter' {
        Write-Host 'Next command:'
        Write-Host '  pwsh -File .\scripts\windows\verify.ps1'
        Write-Host 'Then follow docs/K4-ROUTING.md for routing evidence.'
    }
}
