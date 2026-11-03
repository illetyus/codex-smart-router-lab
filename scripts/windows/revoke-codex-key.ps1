[CmdletBinding(SupportsShouldProcess)]
param(
    [string]$BaseUrl = 'http://127.0.0.1:4000',
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path,
    [string]$RuntimeRoot = (Join-Path $env:LOCALAPPDATA 'CodexSmartRouter'),
    [string]$GatewayEnvPath = '',
    [string]$CodexHome = (Join-Path $env:USERPROFILE '.codex')
)

$ErrorActionPreference = 'Stop'

function Get-DotEnvValue {
    param([string]$Path, [string]$Name)
    if (-not (Test-Path -LiteralPath $Path)) { throw "Required env file not found: $Path" }
    $escaped = [regex]::Escape($Name)
    $line = Get-Content -LiteralPath $Path | Where-Object { $_ -match "^\s*$escaped\s*=\s*.+$" } | Select-Object -First 1
    if ($null -eq $line) { throw "$Name was not found in $Path" }
    return ($line -split '=', 2)[1].Trim()
}

function Protect-SecretFile([string]$Path) {
    $acl = Get-Acl -LiteralPath $Path
    $acl.SetAccessRuleProtection($true, $false)
    foreach ($rule in @($acl.Access)) { [void]$acl.RemoveAccessRuleAll($rule) }
    $sid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User
    $rule = [System.Security.AccessControl.FileSystemAccessRule]::new($sid, [System.Security.AccessControl.FileSystemRights]::FullControl, [System.Security.AccessControl.AccessControlType]::Allow)
    [void]$acl.AddAccessRule($rule)
    Set-Acl -LiteralPath $Path -AclObject $acl
}

if ([string]::IsNullOrWhiteSpace($GatewayEnvPath)) {
    $nativeEnv = Join-Path $RuntimeRoot 'router.env'
    $GatewayEnvPath = if (Test-Path -LiteralPath $nativeEnv) {
        $nativeEnv
    } else {
        Join-Path $RepoRoot '.env'
    }
}
$codexEnv = Join-Path $CodexHome '.env'
$masterKey = Get-DotEnvValue -Path $GatewayEnvPath -Name 'LITELLM_MASTER_KEY'
$virtualKey = Get-DotEnvValue -Path $codexEnv -Name 'LITELLM_API_KEY'
$base = $BaseUrl.TrimEnd('/')
$body = @{ keys = @($virtualKey) } | ConvertTo-Json -Depth 5

if ($PSCmdlet.ShouldProcess('LiteLLM virtual key', 'revoke current Codex gateway key')) {
    $response = Invoke-RestMethod -Method Post -Uri "$base/key/delete" -Headers @{ Authorization = "Bearer $masterKey" } -ContentType 'application/json' -Body $body -TimeoutSec 30
    $remaining = @(Get-Content -LiteralPath $codexEnv | Where-Object { $_ -notmatch '^\s*LITELLM_API_KEY\s*=' })
    if ($remaining.Count -eq 0) {
        Remove-Item -LiteralPath $codexEnv -Force
    } else {
        $remaining | Set-Content -LiteralPath $codexEnv -Encoding utf8NoBOM
        Protect-SecretFile -Path $codexEnv
    }
    Remove-Item -LiteralPath (Join-Path $CodexHome '.env.pre-litellm-applied.sha256') -Force -ErrorAction SilentlyContinue
}

[PSCustomObject]@{ Revoked = $true; CodexEnv = $codexEnv } | ConvertTo-Json -Compress
