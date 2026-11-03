[CmdletBinding()]
param(
    [ValidateSet('subscription','model-probe','autorouter')]
    [string]$Mode = 'subscription',
    [string]$RuntimeRoot = (Join-Path $env:LOCALAPPDATA 'CodexSmartRouter'),
    [string]$UvPath = '',
    [int]$Port = 4000,
    [switch]$NoDatabaseWait
)

$ErrorActionPreference = 'Stop'
$PinnedLiteLLMRef = '4bdeb1378bb19a453cd3c49d383ebe76f057d2c6'
$SourceDir = Join-Path $RuntimeRoot 'litellm-src'
$EnvFile = Join-Path $RuntimeRoot 'router.env'
$ConfigDir = Join-Path $RuntimeRoot 'configs'
$LogDir = Join-Path $RuntimeRoot 'logs'

function Resolve-PostgresCommand([string]$Name) {
    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if ($null -ne $command) { return $command.Source }
    $candidate = Join-Path (Join-Path (Join-Path $env:ProgramFiles 'PostgreSQL') '16') 'bin'
    $candidate = Join-Path $candidate "$Name.exe"
    if (Test-Path -LiteralPath $candidate) { return $candidate }
    return $null
}

function Import-RouterEnv([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Native router env file not found: $Path"
    }

    foreach ($line in Get-Content -LiteralPath $Path) {
        if ([string]::IsNullOrWhiteSpace($line) -or $line.TrimStart().StartsWith('#')) {
            continue
        }
        $pair = $line -split '=', 2
        if ($pair.Count -ne 2) {
            throw "Malformed native router env line in $Path"
        }
        $name = $pair[0].Trim()
        $value = $pair[1]
        if ($name -eq 'OPENAI_API_KEY') {
            throw 'OPENAI_API_KEY is prohibited in the ChatGPT-subscription runtime.'
        }
        [Environment]::SetEnvironmentVariable($name, $value, 'Process')
    }
}

if ([string]::IsNullOrWhiteSpace($UvPath)) {
    $uv = Get-Command uv -ErrorAction SilentlyContinue
    if ($null -eq $uv) { throw 'uv was not found.' }
    $UvPath = $uv.Source
}

if (-not (Test-Path -LiteralPath $SourceDir)) {
    throw "Pinned LiteLLM source directory is missing: $SourceDir"
}

$head = (& git -C $SourceDir rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or $head -ne $PinnedLiteLLMRef) {
    throw "LiteLLM source drift detected. Expected $PinnedLiteLLMRef, got $head"
}

Import-RouterEnv -Path $EnvFile

# A user may legitimately keep an OpenAI Platform key for unrelated software.
# This subscription-only gateway must never inherit it.
[Environment]::SetEnvironmentVariable('OPENAI_API_KEY', $null, 'Process')

foreach ($required in @('DATABASE_URL','LITELLM_MASTER_KEY','LITELLM_SALT_KEY')) {
    $value = [Environment]::GetEnvironmentVariable($required, 'Process')
    if ([string]::IsNullOrWhiteSpace($value)) {
        throw "Required native runtime variable is missing: $required"
    }
}

$env:STORE_MODEL_IN_DB = 'False'
$env:DISABLE_ADMIN_UI = 'True'
$env:NO_DOCS = 'True'
$env:NO_REDOC = 'True'
$env:NO_OPENAPI = 'True'
$env:CHECKPOINT_DISABLE = '1'

# Native processes inherit the user's environment. Clear SSO discovery inputs
# so the no-SSO Admin UI hardening assumption remains identical to Compose.
foreach ($ssoName in @(
    'GOOGLE_CLIENT_ID','GOOGLE_CLIENT_SECRET',
    'MICROSOFT_CLIENT_ID','MICROSOFT_CLIENT_SECRET','MICROSOFT_TENANT',
    'GENERIC_CLIENT_ID','GENERIC_CLIENT_SECRET',
    'SAML_IDP_METADATA_URL','SAML_IDP_METADATA_XML'
)) {
    [Environment]::SetEnvironmentVariable($ssoName, $null, 'Process')
}

$configName = switch ($Mode) {
    'subscription' { 'subscription.yaml' }
    'model-probe' { 'model-probe.yaml' }
    'autorouter' { 'autorouter.yaml' }
}
$configPath = Join-Path $ConfigDir $configName
if (-not (Test-Path -LiteralPath $configPath)) {
    throw "Runtime config is missing: $configPath"
}

if (-not $NoDatabaseWait) {
    $pgReady = Resolve-PostgresCommand 'pg_isready'
    if ([string]::IsNullOrWhiteSpace($pgReady)) {
        throw 'pg_isready was not found. Install PostgreSQL command-line tools.'
    }

    $ready = $false
    for ($i = 0; $i -lt 30; $i++) {
        & $pgReady -d $env:DATABASE_URL -t 2 *> $null
        if ($LASTEXITCODE -eq 0) {
            $ready = $true
            break
        }
        Start-Sleep -Seconds 2
    }
    if (-not $ready) {
        throw 'PostgreSQL did not become ready before the native router startup deadline.'
    }
}

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$logPath = Join-Path $LogDir 'litellm.log'

Push-Location $SourceDir
try {
    & $UvPath run --frozen litellm --config $configPath --host 127.0.0.1 --port $Port *>> $logPath
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
