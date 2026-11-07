$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$logDir=Join-Path $root 'backend\data\background'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log=Join-Path $logDir 'collector.log'
if((Test-Path -LiteralPath $log) -and (Get-Item -LiteralPath $log).Length -gt 2MB){
 Move-Item -LiteralPath $log -Destination ($log+'.previous') -Force
}
try {
 # The logon tasks may start in either order; wait for the backend and its key.
 $ready=$false
 for($i=0;$i -lt 30;$i++){
  try {
   $health=Invoke-RestMethod 'http://127.0.0.1:8787/api/health' -TimeoutSec 2
   if($health.backend -eq 'FastAPI' -and (Test-Path (Join-Path $root 'backend\data\collector-key.txt'))){$ready=$true;break}
  }catch{}
  Start-Sleep -Seconds 2
 }
 if(!$ready){throw 'Network Knight backend did not become ready; Task Scheduler will retry.'}
 & (Join-Path $root 'backend\collector\start-collector.ps1') *>> $log
}catch{
 $_ | Out-String | Add-Content -LiteralPath $log
 exit 1
}
