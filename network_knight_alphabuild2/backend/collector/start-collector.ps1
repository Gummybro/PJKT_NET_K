param([string]$ServerUrl='http://127.0.0.1:8787',[int]$PollSeconds=5,[switch]$Once)
$ErrorActionPreference='Stop'
$projectRoot=Split-Path $PSScriptRoot -Parent
$dataRoot=if($env:NETWORK_KNIGHT_DATA){$env:NETWORK_KNIGHT_DATA}else{Join-Path $projectRoot 'data'}
$keyFile=Join-Path $dataRoot 'collector-key.txt'
$cursorFile=Join-Path $dataRoot 'windows-cursors.json'
if(!(Test-Path -LiteralPath $keyFile)){throw 'Start the Network Knight FastAPI backend first.'}
if($ServerUrl -notmatch '^http://(127\.0\.0\.1|localhost):\d+$'){throw 'This collector supports local backend addresses only.'}
$headers=@{Authorization='Bearer '+(Get-Content -LiteralPath $keyFile -Raw).Trim()}
. (Join-Path $PSScriptRoot 'windows-event.ps1')
$cursors=@{}
if(Test-Path -LiteralPath $cursorFile){$saved=Get-Content -LiteralPath $cursorFile -Raw|ConvertFrom-Json;foreach($p in $saved.PSObject.Properties){$cursors[$p.Name]=[long]$p.Value}}
$channels=@(
 @{Name='Security'},
 @{Name='System'},
 @{Name='Application'},
 @{Name='Microsoft-Windows-Windows Defender/Operational'}
)
Write-Host 'Network Knight Windows collector. Ctrl+C stops collection.' -ForegroundColor Cyan
Write-Host 'Security logs generally require PowerShell opened as Administrator. No audit policies are changed.'
do{
 $problems=@();$sent=0
 foreach($channel in $channels){
  $name=$channel.Name
  try{
   $latest=Get-WinEvent -LogName $name -MaxEvents 1 -ErrorAction Stop
   if(!$cursors.ContainsKey($name)){
    # Bootstrap the newest 50 real records, then follow the saved cursor.
    $cursors[$name]=[Math]::Max(0, [long]$latest.RecordId - 50)
   }
   if([long]$latest.RecordId -lt [long]$cursors[$name]){$cursors[$name]=0;Write-Warning "$name record counter reset; restarting this channel."}
   $query="*[System[(EventRecordID > $($cursors[$name]))]]"
   $records=@()
   try{$records=@(Get-WinEvent -LogName $name -FilterXPath $query -Oldest -MaxEvents 200 -ErrorAction Stop)}catch{if($_.FullyQualifiedErrorId -notlike 'NoMatchingEventsFound*'){throw}}
   if($records.Count -gt 0){
    $events=@($records|ForEach-Object{ConvertFrom-KnightWindowsEvent -Event $_ -Channel $name})
    $payload=@{events=$events}|ConvertTo-Json -Depth 8 -Compress
    $reply=Invoke-RestMethod -Uri "$ServerUrl/api/ingest" -Method Post -Headers $headers -ContentType 'application/json' -Body ([Text.Encoding]::UTF8.GetBytes($payload)) -TimeoutSec 10
    # Only acknowledge the cursor after server acceptance, so failed uploads are retried.
    $cursors[$name]=[long]$records[-1].RecordId;$sent+=$reply.accepted
   }
  }catch{$problems+="$name : $($_.Exception.Message)"}
 }
 $cursors|ConvertTo-Json|Set-Content -LiteralPath ($cursorFile+'.tmp') -Encoding UTF8
 Move-Item -LiteralPath ($cursorFile+'.tmp') -Destination $cursorFile -Force
 $status=if($problems.Count){'degraded'}else{'ok'}
 $detail=if($problems.Count){$problems -join ' | '}else{"Reading 4 Windows channels; uploaded $sent events this poll"}
 try{
  $hb=@{id="windows:$env:COMPUTERNAME";status=$status;detail=$detail}|ConvertTo-Json
  Invoke-RestMethod -Uri "$ServerUrl/api/heartbeat" -Method Post -Headers $headers -ContentType 'application/json' -Body ([Text.Encoding]::UTF8.GetBytes($hb)) -TimeoutSec 10|Out-Null
 }catch{Write-Warning "Backend unreachable: $($_.Exception.Message)"}
 if($problems.Count){foreach($problem in $problems){Write-Warning $problem}}
 if($sent){Write-Host "$(Get-Date -Format T): stored $sent Windows events"}
 if(!$Once){Start-Sleep -Seconds ([Math]::Max(1,$PollSeconds))}
}while(!$Once)
