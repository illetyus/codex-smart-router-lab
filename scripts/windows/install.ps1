[CmdletBinding(SupportsShouldProcess)]
param(
    [ValidateSet('native','docker')]
    [string]$Runtime = 'native',
    [ValidateSet('subscription','model-probe','autorouter')]
    [string]$Mode = 'subscription',
    [string]$RuntimeRoot = (Join-Path $env:LOCALAPPDATA 'CodexSmartRouter'),
    [switch]$SkipTaskRegistration
)

$ErrorActionPreference = 'Stop'
$PinnedLiteLLMRef = '4bdeb1378bb19a453cd3c49d383ebe76f057d2c6'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$ComposeFile = Join-Path $RepoRoot 'docker-compose.yml'

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

function Get-DotEnvValue([string]$Path, [string]$Name) {
    if (-not (Test-Path -LiteralPath $Path)) { return $null }
    $escaped = [regex]::Escape($Name)
    $line = Get-Content -LiteralPath $Path |
        Where-Object { $_ -match "^\s*$escaped\s*=\s*.*$" } |
        Select-Object -First 1
    if ($null -eq $line) { return $null }
    return ($line -split '=', 2)[1].Trim()
}

function Set-DotEnvValue([string]$Path, [string]$Name, [string]$Value) {
    $lines = @()
    if (Test-Path -LiteralPath $Path) {
        $lines = @(Get-Content -LiteralPath $Path)
    }
    $replacement = "$Name=$Value"
    $found = $false
    $updated = foreach ($line in $lines) {
        if ($line -match ("^\s*{0}\s*=" -f [regex]::Escape($Name))) {
            if (-not $found) {
                $replacement
                $found = $true
            }
        }
        else {
            $line
        }
    }
    if (-not $found) {
        $updated = @($updated) + $replacement
    }
    $updated | Set-Content -LiteralPath $Path -Encoding utf8NoBOM
}

function Assert-NoPaidFallback([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) { return }
    $raw = Get-Content -LiteralPath $Path -Raw
    if ($raw -match '(?m)^\s*OPENAI_API_KEY\s*=') {
        throw 'OPENAI_API_KEY is prohibited in this subscription-only lab.'
    }
}

function Assert-EnvFileSafe([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) { return }
    $raw = Get-Content -LiteralPath $Path -Raw
    if ($raw -match 'CHANGE_ME') {
        throw 'existing .env failed validation: placeholder CHANGE_ME value detected.'
    }
    if ($raw -match '(?m)^\s*OPENAI_API_KEY\s*=') {
        throw 'existing .env failed validation: OPENAI_API_KEY is prohibited.'
    }
    foreach ($name in @('LITELLM_MASTER_KEY','LITELLM_SALT_KEY')) {
        $value = Get-DotEnvValue -Path $Path -Name $name
        if (-not [string]::IsNullOrWhiteSpace($value) -and (-not $value.StartsWith('sk-') -or $value.Length -lt 35)) {
            throw "existing .env failed validation: $name is too short or malformed."
        }
    }
    $postgresPassword = Get-DotEnvValue -Path $Path -Name 'POSTGRES_PASSWORD'
    if (-not [string]::IsNullOrWhiteSpace($postgresPassword) -and $postgresPassword.Length -lt 32) {
        throw 'existing .env failed validation: POSTGRES_PASSWORD is too short.'
    }
    $databaseUrl = Get-DotEnvValue -Path $Path -Name 'DATABASE_URL'
    if (-not [string]::IsNullOrWhiteSpace($databaseUrl) -and -not $databaseUrl.StartsWith('postgresql://')) {
        throw 'existing .env failed validation: DATABASE_URL must be a PostgreSQL URL.'
    }
}

& (Join-Path $PSScriptRoot 'preflight.ps1') -Runtime $Runtime
if ($LASTEXITCODE -ne 0) { throw 'Preflight failed.' }

if ($Runtime -eq 'docker') {
    $EnvFile = Join-Path $RepoRoot '.env'
    if (-not (Test-Path -LiteralPath $EnvFile)) {
        @(
            "LITELLM_MASTER_KEY=sk-$(New-RandomHex)",
            "LITELLM_SALT_KEY=sk-$(New-RandomHex)",
            "POSTGRES_PASSWORD=$(New-RandomHex 24)"
        ) | Set-Content -LiteralPath $EnvFile -Encoding utf8NoBOM
    }
    Assert-NoPaidFallback -Path $EnvFile
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

    Write-Host "Docker gateway requested in '$Mode' mode."
    exit 0
}

if ($PSCmdlet.ShouldProcess($RuntimeRoot, "install pinned native LiteLLM in $Mode mode")) {
    [Environment]::SetEnvironmentVariable('OPENAI_API_KEY', $null, 'Process')
    New-Item -ItemType Directory -Force -Path $RuntimeRoot | Out-Null
    $EnvFile = Join-Path $RuntimeRoot 'router.env'

    Assert-NoPaidFallback -Path $EnvFile

    $databaseUrl = Get-DotEnvValue -Path $EnvFile -Name 'DATABASE_URL'
    if ([string]::IsNullOrWhiteSpace($databaseUrl)) {
        if (-not [string]::IsNullOrWhiteSpace($env:DATABASE_URL)) {
            Set-DotEnvValue -Path $EnvFile -Name 'DATABASE_URL' -Value $env:DATABASE_URL
            $databaseUrl = $env:DATABASE_URL
        }
        else {
            throw 'DATABASE_URL is missing. Run provision-postgres.ps1 first.'
        }
    }

    $masterKey = Get-DotEnvValue -Path $EnvFile -Name 'LITELLM_MASTER_KEY'
    if ([string]::IsNullOrWhiteSpace($masterKey)) {
        Set-DotEnvValue -Path $EnvFile -Name 'LITELLM_MASTER_KEY' -Value "sk-$(New-RandomHex)"
    }

    $saltKey = Get-DotEnvValue -Path $EnvFile -Name 'LITELLM_SALT_KEY'
    if ([string]::IsNullOrWhiteSpace($saltKey)) {
        Set-DotEnvValue -Path $EnvFile -Name 'LITELLM_SALT_KEY' -Value "sk-$(New-RandomHex)"
    }

    Assert-NoPaidFallback -Path $EnvFile
    Assert-EnvFileSafe -Path $EnvFile
    Protect-SecretFile -Path $EnvFile

    $SourceDir = Join-Path $RuntimeRoot 'litellm-src'
    if (-not (Test-Path -LiteralPath (Join-Path $SourceDir '.git'))) {
        if (Test-Path -LiteralPath $SourceDir) {
            Remove-Item -LiteralPath $SourceDir -Recurse -Force
        }
        git clone --filter=blob:none --no-checkout https://github.com/BerriAI/litellm.git $SourceDir
        if ($LASTEXITCODE -ne 0) { throw 'LiteLLM source clone failed.' }
    }

    Push-Location $SourceDir
    try {
        git fetch --depth 1 origin $PinnedLiteLLMRef
        if ($LASTEXITCODE -ne 0) { throw 'LiteLLM pinned commit fetch failed.' }
        git checkout --detach $PinnedLiteLLMRef
        if ($LASTEXITCODE -ne 0) { throw 'LiteLLM pinned commit checkout failed.' }

        $head = (& git rev-parse HEAD).Trim()
        if ($LASTEXITCODE -ne 0 -or $head -ne $PinnedLiteLLMRef) {
            throw "LiteLLM source pin verification failed. Expected $PinnedLiteLLMRef, got $head"
        }

        # Reproduce the audited source environment without installing a floating PyPI LiteLLM.
        # uv sync --frozen --python 3.13 --extra proxy --extra extra_proxy
        uv sync --frozen --no-default-groups --no-editable --extra proxy --extra extra_proxy --python 3.13
        if ($LASTEXITCODE -ne 0) { throw 'uv sync failed for the pinned LiteLLM source.' }

        foreach ($line in Get-Content -LiteralPath $EnvFile) {
            if ([string]::IsNullOrWhiteSpace($line) -or $line.TrimStart().StartsWith('#')) { continue }
            $pair = $line -split '=', 2
            if ($pair.Count -eq 2) {
                [Environment]::SetEnvironmentVariable($pair[0].Trim(), $pair[1], 'Process')
            }
        }

        $env:STORE_MODEL_IN_DB = 'False'
        $env:DISABLE_ADMIN_UI = 'True'
        $env:NO_DOCS = 'True'
        $env:NO_REDOC = 'True'
        $env:NO_OPENAPI = 'True'
        $env:CHECKPOINT_DISABLE = '1'

        uv run --frozen prisma generate --schema schema.prisma
        if ($LASTEXITCODE -ne 0) { throw 'prisma generate failed.' }
        uv run --frozen prisma migrate deploy --schema schema.prisma
        if ($LASTEXITCODE -ne 0) { throw 'prisma migrate deploy failed.' }
    }
    finally {
        Pop-Location
    }

    $RuntimeConfigDir = Join-Path $RuntimeRoot 'configs'
    New-Item -ItemType Directory -Force -Path $RuntimeConfigDir | Out-Null
    Copy-Item -LiteralPath (Join-Path $RepoRoot 'configs\litellm\subscription.yaml') -Destination $RuntimeConfigDir -Force
    Copy-Item -LiteralPath (Join-Path $RepoRoot 'configs\litellm\model-probe.yaml') -Destination $RuntimeConfigDir -Force
    Copy-Item -LiteralPath (Join-Path $RepoRoot 'configs\litellm\autorouter.yaml') -Destination $RuntimeConfigDir -Force

    $InstalledLauncher = Join-Path $RuntimeRoot 'start-router.ps1'
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'start-router.ps1') -Destination $InstalledLauncher -Force

    $manifest = [ordered]@{
        runtime = 'native'
        mode = $Mode
        litellm_commit = $PinnedLiteLLMRef
        python = '3.13'
        source_dir = $SourceDir
        config_dir = $RuntimeConfigDir
    }
    $manifest | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $RuntimeRoot 'install-manifest.json') -Encoding utf8NoBOM

    if (-not $SkipTaskRegistration) {
        $uvPath = (Get-Command uv -ErrorAction Stop).Source
        & (Join-Path $PSScriptRoot 'register-router-task.ps1') -Mode $Mode -RuntimeRoot $RuntimeRoot -UvPath $uvPath | Out-Null
    }
}

Write-Host "Native gateway installed in '$Mode' mode at $RuntimeRoot."
Write-Host 'Next: verify health, provision the restricted Codex key, configure the Codex provider, fully restart ChatGPT Desktop, and run the K2 live probe.'
