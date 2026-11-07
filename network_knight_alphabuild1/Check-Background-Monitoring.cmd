@echo off
powershell.exe -NoProfile -Command "Get-ScheduledTask -TaskName 'Network Knight*' -ErrorAction SilentlyContinue | Select-Object TaskName,State; try{$s=Invoke-RestMethod 'http://127.0.0.1:8787/api/state?dataset=live' -TimeoutSec 5; $s.collectors | ForEach-Object { [pscustomobject]@{Collector=$_.id;Status=$(if(([DateTimeOffset]::Now-[DateTimeOffset]::Parse($_.last_seen)).TotalSeconds -gt 30){'offline'}else{$_.status});LastSeen=$_.last_seen;Detail=$_.detail} } | Format-List}catch{Write-Host 'Backend not reachable.'}"
pause
