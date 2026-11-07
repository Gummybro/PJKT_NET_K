@echo off
powershell.exe -NoProfile -Command "try{$s=Invoke-RestMethod 'http://127.0.0.1:8787/api/state' -TimeoutSec 5; Write-Host ('Network Knight: '+$s.monitoring_status); $s.services | Select-Object name,state,pid,last_seen,detail | Format-List}catch{Write-Host 'OFFLINE: Network Knight is not responding. Run Start-Network-Knight.cmd.' -ForegroundColor Red}"
pause
