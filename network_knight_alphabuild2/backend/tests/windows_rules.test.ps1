$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '..\collector\windows-event.ps1')
$mapping=@{4740='account_locked';4726='account_deleted';4732='group_member_added';4728='group_member_added';4756='group_member_added';4719='audit_policy_changed';4698='scheduled_task_created';5001='defender_disabled'}
foreach($eventId in $mapping.Keys){
 $fixture=[pscustomobject]@{Id=$eventId;RecordId=42;TimeCreated=[DateTime]::UtcNow;MachineName='fixture';ProviderName='fixture';Message='SAMPLE fixture'}
 $fixture|Add-Member ScriptMethod ToXml { '<Event><EventData><Data Name="TargetSid">S-1-5-32-544</Data><Data Name="TargetUserName">Administrators</Data></EventData></Event>' }
 $channel=if($eventId -eq 5001){'Microsoft-Windows-Windows Defender/Operational'}else{'Security'}
 $parsed=ConvertFrom-KnightWindowsEvent -Event $fixture -Channel $channel
 if($parsed.kind -ne $mapping[$eventId]){throw "Incorrect mapping for $eventId"}
 if($parsed.details.fields.TargetSid -ne 'S-1-5-32-544'){throw 'Group SID evidence lost'}
}
Write-Host 'PASS: 8 Windows event mappings and retained group SID evidence (fixtures only)'
