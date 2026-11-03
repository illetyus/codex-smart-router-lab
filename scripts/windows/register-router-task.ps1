[CmdletBinding(SupportsShouldProcess)]
param(
    [ValidateSet('subscription','model-probe','autorouter')]
    [string]$Mode = 'subscription',
    [string]$RuntimeRoot = (Join-Path $env:LOCALAPPDATA 'CodexSmartRouter'),
    [string]$UvPath = '',
    [string]$TaskName = 'Codex Smart Router'
)

$ErrorActionPreference = 'Stop'
$launcher = Join-Path $RuntimeRoot 'start-router.ps1'
if (-not (Test-Path -LiteralPath $launcher)) {
    throw "Installed launcher not found: $launcher"
}

if ([string]::IsNullOrWhiteSpace($UvPath)) {
    $uv = Get-Command uv -ErrorAction SilentlyContinue
    if ($null -eq $uv) { throw 'uv was not found.' }
    $UvPath = $uv.Source
}

$pwsh = (Get-Command pwsh -ErrorAction Stop).Source
$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name

$arguments = @(
    '-NoLogo',
    '-NoProfile',
    '-NonInteractive',
    '-WindowStyle', 'Hidden',
    '-ExecutionPolicy', 'Bypass',
    '-File', ('"{0}"' -f $launcher),
    '-Mode', $Mode,
    '-RuntimeRoot', ('"{0}"' -f $RuntimeRoot),
    '-UvPath', ('"{0}"' -f $UvPath)
) -join ' '

$action = New-ScheduledTaskAction -Execute $pwsh -Argument $arguments
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $identity
$principal = New-ScheduledTaskPrincipal -UserId $identity -LogonType Interactive -RunLevel Limited
$settingsArgs = @{
    StartWhenAvailable = $true
    RestartCount = 3
    RestartInterval = (New-TimeSpan -Minutes 1)
    MultipleInstances = 'IgnoreNew'
    ExecutionTimeLimit = [TimeSpan]::Zero
}
$settings = New-ScheduledTaskSettingsSet @settingsArgs

if ($PSCmdlet.ShouldProcess($TaskName, "register current-user LiteLLM task in $Mode mode")) {
    $registerArgs = @{
        TaskName = $TaskName
        Action = $action
        Trigger = $trigger
        Principal = $principal
        Settings = $settings
        Description = 'Local Codex Smart Router. Binds LiteLLM to 127.0.0.1 only.'
        Force = $true
    }
    Register-ScheduledTask @registerArgs | Out-Null
    Start-ScheduledTask -TaskName $TaskName
}

[PSCustomObject]@{
    TaskName = $TaskName
    Mode = $Mode
    RuntimeRoot = $RuntimeRoot
    User = $identity
} | ConvertTo-Json -Compress
