[CmdletBinding(SupportsShouldProcess)]
param(
    [ValidateSet('subscription','autorouter')]
    [string]$Mode = 'subscription'
)

$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$EnvFile = Join-Path $RepoRoot '.env'
$ComposeFile = Join-Path $RepoRoot 'docker-compose.yml'

& (Join-Path $PSScriptRoot 'preflight.ps1')
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

$config = if ($Mode -eq 'autorouter') { 'autorouter.yaml' } else { 'subscription.yaml' }
$env:CODEX_ROUTER_CONFIG = $config

if ($PSCmdlet.ShouldProcess('local Docker stack', "build and start LiteLLM in $Mode mode")) {
    docker compose -f $ComposeFile up -d --build
    if ($LASTEXITCODE -ne 0) { throw 'docker compose up failed.' }
}

Write-Host "Gateway requested in '$Mode' mode."
Write-Host 'Next: create a LiteLLM virtual key, store it as LITELLM_API_KEY in %USERPROFILE%\.codex\.env, then merge configs/codex/provider.subscription.toml into Codex config.toml.'
