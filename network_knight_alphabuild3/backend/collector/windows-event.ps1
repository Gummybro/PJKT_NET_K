function ConvertFrom-KnightWindowsEvent {
 param([Parameter(Mandatory)]$Event,[Parameter(Mandatory)][string]$Channel)
 [xml]$xml=$Event.ToXml()
 $fields=@{}
 foreach($item in $xml.Event.EventData.Data){if($null -ne $item -and $item.Name){$fields[[string]$item.Name]=[string]$item.'#text'}}
 $kind=switch([int]$Event.Id){4800{if($Channel -eq 'Security'){'workstation_locked'}else{'windows_event'}}4625{'auth_failure'}4624{'auth_success'}1102{'audit_cleared'}4720{'account_created'}4697{'service_installed'}7045{'service_installed'}1116{'malware_detected'}1117{'malware_action'}4740{'account_locked'}4726{'account_deleted'}4732{'group_member_added'}4728{'group_member_added'}4756{'group_member_added'}4719{'audit_policy_changed'}4698{'scheduled_task_created'}5001{'defender_disabled'}default{'windows_event'}}
 $severity=switch($kind){'audit_cleared'{'critical'}'malware_detected'{'high'}'account_created'{'medium'}'service_installed'{'medium'}'auth_failure'{'low'}'account_locked'{'medium'}'account_deleted'{'medium'}'group_member_added'{'medium'}'audit_policy_changed'{'high'}'scheduled_task_created'{'medium'}'defender_disabled'{'high'}default{switch([int]$Event.Level){1{'critical'}2{'high'}3{'medium'}default{'info'}}}}
 $ip=if($fields.IpAddress -and $fields.IpAddress -ne '-'){$fields.IpAddress}else{'unknown'}
 $user=if($fields.TargetUserName){$fields.TargetUserName}elseif($fields.SubjectUserName){$fields.SubjectUserName}else{'unknown'}
 $message=if($Event.Message){[string]$Event.Message}else{"Windows event $($Event.Id) from $($Event.ProviderName)"}
 # Timestamp in external id avoids collisions if a Windows log is cleared and record ids are reused.
 @{
  source="windows:$Channel";external_id="$($Event.RecordId):$($Event.TimeCreated.ToUniversalTime().ToString('o'))"
  timestamp=$Event.TimeCreated.ToUniversalTime().ToString('o');kind=$kind;severity=$severity
  host=[string]$Event.MachineName;ip=$ip;username=$user;message=$message
  details=@{event_id=[int]$Event.Id;record_id=[long]$Event.RecordId;provider=[string]$Event.ProviderName;fields=$fields}
 }
}


