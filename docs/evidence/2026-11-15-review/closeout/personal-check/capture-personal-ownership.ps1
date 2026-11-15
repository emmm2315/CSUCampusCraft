$ErrorActionPreference='Stop'
$repo='D:\Github Projects\CSUCampusCraft'
$out=Join-Path $repo 'docs\evidence\2026-11-15-review\closeout\personal-check'
$state=Get-Content -LiteralPath (Join-Path $out 'state.json') -Raw | ConvertFrom-Json -AsHashtable
$all=@(Get-CimInstance Win32_Process)
$dbListener=@(Get-NetTCPConnection -State Listen -LocalPort $state.dbPort -ErrorAction Stop)
$dbOwner=@($dbListener.OwningProcess | Select-Object -Unique)
if($dbOwner.Count -ne 1){throw 'Isolated MySQL listener has unexpected ownership'}
$state.mysqlListeningPid=[int]$dbOwner[0]
$ids=@([int]$state.mysqlStartedPid,[int]$state.mysqlListeningPid,[int]$state.userPid,[int]$state.adminPid)|Select-Object -Unique
$processes=@($all | Where-Object {$_.ProcessId -in $ids})
foreach($side in @('user','admin')) {
  $appId=if($side -eq 'user'){$state.userPid}else{$state.adminPid}
  $port=if($side -eq 'user'){$state.userPort}else{$state.adminPort}
  $p=@($processes | Where-Object {$_.ProcessId -eq $appId})
  if($p.Count -ne 1 -or $p[0].Name -ne 'java.exe' -or $p[0].CommandLine -notlike "*-jar csucampuscraft-$side/target/csucampuscraft-$side-0.0.1-SNAPSHOT.jar*"){throw "Java process ownership mismatch $side"}
  $listen=@(Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction Stop)
  if(@($listen | Where-Object {$_.OwningProcess -ne $appId}).Count -ne 0){throw "HTTP ownership mismatch $side"}
}
$mysqlProc=@($processes | Where-Object {$_.ProcessId -eq $state.mysqlListeningPid})
if($mysqlProc.Count -ne 1 -or $mysqlProc[0].Name -ne 'mysqld.exe' -or $mysqlProc[0].CommandLine -notlike "*--datadir=$($state.datadir)*" -or $mysqlProc[0].CommandLine -notlike "*--port=$($state.dbPort)*"){throw 'MySQL datadir/port process mismatch'}
$connections=@(Get-NetTCPConnection | Where-Object {$_.OwningProcess -in $ids -and ($_.State -eq 'Listen' -or $_.RemotePort -eq $state.dbPort)} | Select-Object LocalAddress,LocalPort,RemoteAddress,RemotePort,State,OwningProcess)
$sql="SELECT p.ID,p.USER,p.DB,p.HOST,v.VARIABLE_VALUE AS time_zone FROM information_schema.PROCESSLIST p JOIN performance_schema.threads t ON t.PROCESSLIST_ID=p.ID JOIN performance_schema.variables_by_thread v ON v.THREAD_ID=t.THREAD_ID AND v.VARIABLE_NAME='time_zone' WHERE p.USER='$($state.dbUser)' AND p.DB='$($state.database)' ORDER BY p.ID;"
$lines=@(& D:\MySQL\bin\mysql.exe "--defaults-file=$($state.rootConfig)" --skip-password --batch --raw "--execute=$sql")
$exit=$LASTEXITCODE
if($exit -ne 0){throw 'Cannot inspect actual JDBC sessions'}
$rows=@($lines | ConvertFrom-Csv -Delimiter "`t")
$owners=@(foreach($row in $rows){
  $clientPort=[int]($row.HOST -replace '^.*:','')
  $mapped=@($connections | Where-Object {$_.LocalPort -eq $clientPort -and $_.RemotePort -eq $state.dbPort})
  [pscustomobject]@{connectionId=$row.ID;database=$row.DB;dbUser=$row.USER;clientPort=$clientPort;timeZone=$row.time_zone;javaPid=if($mapped.Count -eq 1){$mapped[0].OwningProcess}else{$null};side=if($mapped.OwningProcess -contains $state.userPid){'user'}elseif($mapped.OwningProcess -contains $state.adminPid){'admin'}else{'unmapped'}}
})
if($owners.Count -eq 0 -or @($owners|Where-Object {$_.timeZone -ne '+00:00' -or $_.side -eq 'unmapped'}).Count -ne 0){throw 'JDBC UTC/ownership could not be proven'}
$os=Get-CimInstance Win32_OperatingSystem | Select-Object Caption,Version,BuildNumber,OSArchitecture
$result=@{capturedAt=(Get-Date -Format o);executor='AI setup observation, not human acceptance';processes=@($processes|Select-Object ProcessId,ParentProcessId,Name,CommandLine,ExecutablePath,CreationDate);connections=$connections;jdbcSql=$sql;jdbcQueryExitCode=$exit;jdbcSessions=$owners;jdbcUtcAll=$true;os=$os;osTimeZone=(Get-TimeZone|Select-Object Id,BaseUtcOffset,SupportsDaylightSavingTime);serverProcessExitCodes=@{user=$null;admin=$null;mysql=$null};note='Processes are intentionally running while awaiting human steps. Null exit code does not mean success or failure.'}
$result|ConvertTo-Json -Depth 10|Set-Content -LiteralPath (Join-Path $out 'process-and-jdbc-ownership.json') -Encoding utf8
$state.phase='READY for human step1; AI login precheck and SQL fixture completed only'
$state|ConvertTo-Json -Depth 10|Set-Content -LiteralPath (Join-Path $out 'state.json') -Encoding utf8
$pointerPath=Join-Path ([IO.Path]::GetTempPath()) 'personal-check-connection.json'
$pointer=Get-Content -LiteralPath $pointerPath -Raw|ConvertFrom-Json -AsHashtable
$pointer.mysql_listening_pid=$state.mysqlListeningPid
$pointer|ConvertTo-Json -Depth 8|Set-Content -LiteralPath $pointerPath -Encoding utf8
Write-Output ('USER_PID='+$state.userPid)
Write-Output ('ADMIN_PID='+$state.adminPid)
Write-Output ('MYSQL_STARTED_PID='+$state.mysqlStartedPid)
Write-Output ('MYSQL_LISTEN_PID='+$state.mysqlListeningPid)
Write-Output ('JDBC_UTC_COUNT='+$owners.Count)
