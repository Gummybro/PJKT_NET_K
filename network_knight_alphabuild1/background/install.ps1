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
$collectorAction=New-ScheduledTaskAction -Execute "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -Argument ('-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy RemoteSigned -File "'+(Join-Path $root 'background\collector_runner.ps1')+'"') -WorkingDirectory $root
$backendPrincipal=New-ScheduledTaskPrincipal -UserId $identity.Name -LogonType Interactive -RunLevel Limited
$collectorPrincipal=New-ScheduledTaskPrincipal -UserId $identity.Name -LogonType Interactive -RunLevel Highest
Register-ScheduledTask -TaskName 'Network Knight Backend' -Action $backendAction -Trigger $trigger -Settings $settings -Principal $backendPrincipal -Description 'Local Network Knight FastAPI backend. No browser needed.' -Force | Out-Null
Register-ScheduledTask -TaskName 'Network Knight Collector' -Action $collectorAction -Trigger $trigger -Settings $settings -Principal $collectorPrincipal -Description 'Collect supported local Windows events for Network Knight.' -Force | Out-Null
# Do not stop an existing foreground backend or collector. They can be closed
# after installation; retry settings allow the tasks to recover from a busy port.
Start-ScheduledTask -TaskName 'Network Knight Backend'
Start-ScheduledTask -TaskName 'Network Knight Collector'
Write-Host 'Background monitoring installed. Close the old manual server/collector windows to avoid duplicate collectors.' -ForegroundColor Green
Write-Host 'Tasks start at your Windows sign-in and run without a browser. They retry failed starts every minute.'
Write-Host 'Check Data Sources for a fresh Windows collector heartbeat. Closing the browser has no effect.'
Write-Host 'The laptop must be awake. Signing out, sleep or shutdown stops monitoring until you sign in/resume.'
