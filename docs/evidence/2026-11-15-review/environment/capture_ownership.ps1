$ErrorActionPreference='Stop'
$out='D:\Github Projects\CSUCampusCraft\docs\evidence\2026-11-15-review\environment'
$s=Get-Content (Join-Path $out 'state.json') -Raw | ConvertFrom-Json
$short=Get-Content (Join-Path $out 'short-ttl-state.json') -Raw | ConvertFrom-Json
$all=Get-CimInstance Win32_Process
$parents=@($s.mysqlPid,$s.userPid,$s.adminPid,$short.pid)
$processes=@($all | Where-Object {$_.ProcessId -in $parents -or $_.ParentProcessId -eq $s.mysqlPid})
$processes | Select-Object ProcessId,ParentProcessId,Name,CommandLine,ExecutablePath | ConvertTo-Json -Depth 4 | Set-Content (Join-Path $out 'process-ownership-final.json') -Encoding utf8
$connections=@(Get-NetTCPConnection | Where-Object { $_.OwningProcess -in $processes.ProcessId -and ($_.State -eq 'Listen' -or $_.RemotePort -eq $s.dbPort) } | Select-Object LocalAddress,LocalPort,RemoteAddress,RemotePort,State,OwningProcess)
$connections | ConvertTo-Json -Depth 4 | Set-Content (Join-Path $out 'tcp-ownership.json') -Encoding utf8
$sql="SELECT p.ID,p.USER,p.DB,p.HOST,v.VARIABLE_VALUE time_zone FROM information_schema.PROCESSLIST p JOIN performance_schema.threads t ON t.PROCESSLIST_ID=p.ID JOIN performance_schema.variables_by_thread v ON v.THREAD_ID=t.THREAD_ID AND v.VARIABLE_NAME='time_zone' WHERE p.USER='review_app' ORDER BY p.ID;"
$sql | Set-Content (Join-Path $out 'jdbc-session-owners.sql') -Encoding utf8
$lines=@(& D:\MySQL\bin\mysql.exe "--defaults-file=$($s.rootConfig)" --skip-password --batch --raw "--execute=$sql")
$lines | Set-Content (Join-Path $out 'jdbc-session-owners-raw.tsv') -Encoding utf8
$rows=@($lines | ConvertFrom-Csv -Delimiter "`t")
$owners=@(foreach($row in $rows){
  $clientPort=[int]($row.HOST -replace '^.*:','')
  $match=@($connections | Where-Object {$_.LocalPort -eq $clientPort -and $_.RemotePort -eq $s.dbPort})
  [pscustomobject]@{connectionId=$row.ID;dbUser=$row.USER;database=$row.DB;clientPort=$clientPort;timeZone=$row.time_zone;javaPid=if($match.Count -eq 1){$match[0].OwningProcess}else{$null};side=if($match.OwningProcess -contains $s.userPid){'user-default'}elseif($match.OwningProcess -contains $s.adminPid){'admin'}elseif($match.OwningProcess -contains $short.pid){'user-short-ttl'}else{'unmapped'}}
})
$owners | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $out 'jdbc-session-owners.json') -Encoding utf8
$mysqlListen=@($connections | Where-Object {$_.LocalPort -eq $s.dbPort -and $_.State -eq 'Listen'}).OwningProcess | Select-Object -Unique
@{mysqlStartedPid=$s.mysqlPid;mysqlListeningPid=$mysqlListen;userPid=$s.userPid;adminPid=$s.adminPid;shortUserPid=$short.pid;capturedAt=(Get-Date -Format o);utcAll=(@($owners|Where-Object {$_.timeZone -ne '+00:00'}).Count -eq 0);sideCounts=@($owners|Group-Object side|Select-Object Name,Count)} | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $out 'ownership-summary.json') -Encoding utf8
Add-Content -LiteralPath (Join-Path (Split-Path $out) 'commands-environment.md') -Encoding utf8 -Value '`pwsh -NoProfile -File environment/capture_ownership.ps1 (CIM, Get-NetTCPConnection, MySQL processlist+time_zone join)`'
Write-Output ('MYSQL_LISTENER_PID='+($mysqlListen -join ','))
