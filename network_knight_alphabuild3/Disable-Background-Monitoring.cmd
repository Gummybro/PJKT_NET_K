@echo off
powershell.exe -NoProfile -Command "$ErrorActionPreference='Stop'; foreach($name in @('Network Knight Collector','Network Knight Backend')){ $task=Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue; if($task){Stop-ScheduledTask -TaskName $name; Unregister-ScheduledTask -TaskName $name -Confirm:$false} }; Write-Host 'Background tasks removed. Saved events and alerts are preserved.'"
pause
