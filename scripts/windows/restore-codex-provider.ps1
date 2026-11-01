[CmdletBinding(SupportsShouldProcess)]
param(
    [string]$CodexHome = (Join-Path $env:USERPROFILE '.codex')
)

$ErrorActionPreference = 'Stop'
$configPath = Join-Path $CodexHome 'config.toml'
$configBackup = Join-Path $CodexHome 'config.toml.pre-litellm-backup'
$envPath = Join-Path $CodexHome '.env'
$envBackup = Join-Path $CodexHome '.env.pre-litellm-backup'
$configAppliedHashPath = Join-Path $CodexHome 'config.toml.pre-litellm-applied.sha256'
$envAppliedHashPath = Join-Path $CodexHome '.env.pre-litellm-applied.sha256'

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

function Save-ConflictCopyIfDrifted {
    param([string]$Path, [string]$AppliedHashPath, [string]$Label)
    if (-not (Test-Path -LiteralPath $Path) -or -not (Test-Path -LiteralPath $AppliedHashPath)) { return $null }
    $expected = (Get-Content -LiteralPath $AppliedHashPath -Raw).Trim()
    $actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash
    if ($actual -eq $expected) { return $null }
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $copy = Join-Path $CodexHome "$Label.pre-litellm-restore-conflict-$stamp"
    Copy-Item -LiteralPath $Path -Destination $copy -Force
    if ($Label -eq '.env') { Protect-SecretFile -Path $copy }
    return $copy
}

if (-not (Test-Path -LiteralPath $configBackup)) {
    throw "Codex config backup was not found: $configBackup"
}

$configConflict = Save-ConflictCopyIfDrifted -Path $configPath -AppliedHashPath $configAppliedHashPath -Label 'config.toml'
if ($PSCmdlet.ShouldProcess($configPath, 'restore pre-LiteLLM Codex configuration')) {
    Copy-Item -LiteralPath $configBackup -Destination $configPath -Force
    Remove-Item -LiteralPath $configAppliedHashPath -Force -ErrorAction SilentlyContinue
}

$envAction = 'unchanged'
$envConflict = Save-ConflictCopyIfDrifted -Path $envPath -AppliedHashPath $envAppliedHashPath -Label '.env'
if (Test-Path -LiteralPath $envBackup) {
    if ($PSCmdlet.ShouldProcess($envPath, 'restore pre-LiteLLM Codex dotenv')) {
        Copy-Item -LiteralPath $envBackup -Destination $envPath -Force
    }
    $envAction = 'restored-backup'
}
elseif (Test-Path -LiteralPath $envPath) {
    $remaining = @(
        Get-Content -LiteralPath $envPath |
            Where-Object { $_ -notmatch '^\s*LITELLM_API_KEY\s*=' }
    )
    if ($PSCmdlet.ShouldProcess($envPath, 'remove LiteLLM virtual key from Codex dotenv')) {
        $remaining | Set-Content -LiteralPath $envPath -Encoding utf8NoBOM
    }
    $envAction = 'removed-litellm-key'
}
Remove-Item -LiteralPath $envAppliedHashPath -Force -ErrorAction SilentlyContinue

[PSCustomObject]@{
    Config = $configPath
    ConfigBackup = $configBackup
    Env = $envPath
    EnvAction = $envAction
    ConfigConflictCopy = $configConflict
    EnvConflictCopy = $envConflict
} | ConvertTo-Json -Compress
