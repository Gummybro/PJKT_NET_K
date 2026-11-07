$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$identity=[Security.Principal.WindowsIdentity]::GetCurrent()
$principal=[Security.Principal.WindowsPrincipal]::new($identity)
if(!$principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){
 throw 'Administrator access is required to register the Windows log collector task. Right-click Enable-Background-Monitoring.cmd and choose Run as administrator.'
}
$python=Join-Path $root '.venv\Scripts\pythonw.exe'
if(!(Test-Path -LiteralPath $python)){
 $python=Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\pythonw.exe'
 if(!(Test-Path -LiteralPath $python) -or !(Test-Path (Join-Path $root '.python-packages\fastapi'))){
  throw 'Run Setup-Windows.cmd first to install Python dependencies.'
 }
}
$trigger=New-ScheduledTaskTrigger -AtLogOn -User $identity.Name
$settings=New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -MultipleInstances IgnoreNew
$backendAction=New-ScheduledTaskAction -Execute $python -Argument ('"'+(Join-Path $root 'background\backend_runner.py')+'"') -WorkingDirectory $root
$backendPrincipal=New-ScheduledTaskPrincipal -UserId $identity.Name -LogonType Interactive -RunLevel Highest
Register-ScheduledTask -TaskName 'Network Knight Backend' -Action $backendAction -Trigger $trigger -Settings $settings -Principal $backendPrincipal -Description 'Network Knight server and both supervised collectors. No browser needed.' -Force | Out-Null
# Retire the old separate collector task so collection is supervised only once.
$legacy=Get-ScheduledTask -TaskName 'Network Knight Collector' -ErrorAction SilentlyContinue
if($legacy){Stop-ScheduledTask -TaskName 'Network Knight Collector';Unregister-ScheduledTask -TaskName 'Network Knight Collector' -Confirm:$false}
Start-ScheduledTask -TaskName 'Network Knight Backend'
Write-Host 'One background task now starts FastAPI and both managed collectors.' -ForegroundColor Green
Write-Host 'Stop a manually running copy first. Open the dashboard to confirm component health.'
Write-Host 'The task starts at sign-in; the laptop must be awake. Saved component disable choices are respected.'
