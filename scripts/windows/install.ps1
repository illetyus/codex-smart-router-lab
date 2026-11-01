[CmdletBinding(SupportsShouldProcess)]
param(
    [ValidateSet('subscription','model-probe','autorouter')]
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

function Protect-SecretFile([string]$Path) {
    $acl = Get-Acl -LiteralPath $Path
    $acl.SetAccessRuleProtection($true, $false)
    foreach ($rule in @($acl.Access)) {
        [void]$acl.RemoveAccessRuleAll($rule)
    }
    $sid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User
    $rule = [System.Security.AccessControl.FileSystemAccessRule]::new(
        $sid,
        [System.Security.AccessControl.FileSystemRights]::FullControl,
        [System.Security.AccessControl.AccessControlType]::Allow
    )
    [void]$acl.AddAccessRule($rule)
    Set-Acl -LiteralPath $Path -AclObject $acl
}

function Assert-EnvFileSafe([string]$Path) {
    $raw = Get-Content -LiteralPath $Path -Raw
    if ($raw -match '(?m)^\s*OPENAI_API_KEY\s*=') {
        throw 'existing .env failed validation: OPENAI_API_KEY is prohibited in this subscription-only lab.'
    }
    if ($raw -match 'CHANGE_ME') {
        throw 'existing .env failed validation: placeholder CHANGE_ME value detected.'
    }
    foreach ($name in @('LITELLM_MASTER_KEY','LITELLM_SALT_KEY','POSTGRES_PASSWORD')) {
        $match = [regex]::Match($raw, "(?m)^\s*$name\s*=\s*(.+)\s*$")
        if (-not $match.Success) { throw "existing .env failed validation: missing $name." }
        $value = $match.Groups[1].Value.Trim()
        if ($name -like 'LITELLM_*' -and (-not $value.StartsWith('sk-') -or $value.Length -lt 35)) {
            throw "existing .env failed validation: $name is too short or malformed."
        }
        if ($name -eq 'POSTGRES_PASSWORD' -and $value.Length -lt 32) {
            throw 'existing .env failed validation: POSTGRES_PASSWORD is too short.'
        }
    }
}

if (-not (Test-Path $EnvFile)) {
    @(
        "LITELLM_MASTER_KEY=sk-$(New-RandomHex)",
        "LITELLM_SALT_KEY=sk-$(New-RandomHex)",
        "POSTGRES_PASSWORD=$(New-RandomHex 24)"
    ) | Set-Content -Path $EnvFile -Encoding utf8NoBOM
}
Assert-EnvFileSafe -Path $EnvFile
Protect-SecretFile -Path $EnvFile

$config = switch ($Mode) {
    'subscription' { 'subscription.yaml' }
    'model-probe' { 'model-probe.yaml' }
    'autorouter' { 'autorouter.yaml' }
}
$env:CODEX_ROUTER_CONFIG = $config

if ($PSCmdlet.ShouldProcess('local Docker stack', "build and start LiteLLM in $Mode mode")) {
    docker compose -f $ComposeFile up -d --build
    if ($LASTEXITCODE -ne 0) { throw 'docker compose up failed.' }
}

Write-Host "Gateway requested in '$Mode' mode."
Write-Host 'Next: create a LiteLLM virtual key, store it as LITELLM_API_KEY in %USERPROFILE%\.codex\.env, then merge configs/codex/provider.subscription.toml into Codex config.toml.'
