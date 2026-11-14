$ErrorActionPreference='Stop'
$repo='D:\Github Projects\CSUCampusCraft'
Set-Location -LiteralPath $repo
$out=Join-Path $repo 'docs\evidence\2026-11-15-review\environment'
$s=Get-Content (Join-Path $out 'state.json') -Raw | ConvertFrom-Json
$connPath=Join-Path ([IO.Path]::GetTempPath()) 'review-connection.json'
$conn=Get-Content $connPath -Raw | ConvertFrom-Json
$mysql='D:\MySQL\bin\mysql.exe'
$mysqladmin='D:\MySQL\bin\mysqladmin.exe'
$uuidExpected='8323950c-e04c-11f1-bb8f-005056c00001'
$target=@(& $mysql "--defaults-file=$($s.rootConfig)" --skip-password --batch --raw --skip-column-names --execute='SELECT @@port,@@datadir,@@server_uuid;')
$targetExit=$LASTEXITCODE
if($targetExit -ne 0){throw '不能确认当前隔离实例；拒绝停止'}
$fields=$target[0] -split "`t"
$normalize={param([string]$p) ($p -replace '\\','/').TrimEnd('/')}
if([int]$fields[0] -ne $s.dbPort -or (& $normalize $fields[1]) -ne (& $normalize $s.datadir) -or $fields[2] -ne $uuidExpected){throw '隔离datadir/UUID/port不匹配；拒绝停止'}
$appPids=@([int]$conn.user_pid,[int]$conn.admin_pid)
$mysqlPids=@([int]$s.mysqlPid,29576)
$all=Get-CimInstance Win32_Process
$before=@($all|Where-Object {$_.ProcessId -in ($appPids+$mysqlPids)}|Select-Object ProcessId,ParentProcessId,Name,CommandLine,ExecutablePath,CreationDate)
if($before.Count -ne 4){throw '预期四个本轮进程不全；拒绝停止'}
foreach($side in @('user','admin')){
 $appPid=if($side -eq 'user'){$conn.user_pid}else{$conn.admin_pid}
 $port=if($side -eq 'user'){8080}else{8081}
 $p=@($before|Where-Object {$_.ProcessId -eq $appPid})[0]
 if($p.Name -ne 'java.exe' -or $p.ExecutablePath -ne 'C:\Users\Starmetor\.jdks\ms-21.0.12.1\bin\java.exe' -or $p.CommandLine -notlike "*-jar csucampuscraft-$side/target/csucampuscraft-$side-0.0.1-SNAPSHOT.jar"){throw "Java归属不匹配 $side"}
 $listeners=@(Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)
 if($listeners.Count -eq 0 -or @($listeners|Where-Object {$_.OwningProcess -ne $appPid}).Count -ne 0){throw "端口归属不匹配 $side"}
}
foreach($mysqlPid in $mysqlPids){
 $p=@($before|Where-Object {$_.ProcessId -eq $mysqlPid})[0]
 if($p.Name -ne 'mysqld.exe' -or $p.ExecutablePath -ne 'D:\MySQL\bin\mysqld.exe' -or $p.CommandLine -notlike "*--datadir=$($s.datadir)*" -or $p.CommandLine -notlike "*--port=$($s.dbPort)*"){throw 'MySQL命令归属不匹配'}
}
if(@($before|Where-Object {$_.ProcessId -eq 29576})[0].ParentProcessId -ne $s.mysqlPid){throw 'MySQL父子归属不匹配'}
$dbListeners=@(Get-NetTCPConnection -LocalPort $s.dbPort -State Listen -ErrorAction SilentlyContinue)
if($dbListeners.Count -eq 0 -or @($dbListeners|Where-Object {$_.OwningProcess -ne 29576}).Count -ne 0){throw 'MySQL监听归属不匹配'}
$beforeListeners=@(Get-NetTCPConnection -State Listen|Where-Object {$_.OwningProcess -in ($appPids+$mysqlPids)}|Select-Object LocalAddress,LocalPort,State,OwningProcess)
@{capturedAt=(Get-Date -Format o);targetQueryExitCode=$targetExit;target=$target;processes=$before;listeners=$beforeListeners}|ConvertTo-Json -Depth 6|Set-Content (Join-Path $out 'final-stop-before.json') -Encoding utf8
$exitRecords=@()
$dbHandles=@{}
foreach($mysqlPid in $mysqlPids){$proc=Get-Process -Id $mysqlPid;$null=$proc.Handle;$dbHandles[$mysqlPid]=$proc}
foreach($appPid in $appPids){
 $proc=Get-Process -Id $appPid
 $null=$proc.Handle
 Stop-Process -Id $appPid
 $wait=$proc.WaitForExit(10000)
 $nativeExit=$null
 if($wait){$nativeExit=$proc.ExitCode}
 $exitRecords+=@{pid=$appPid;operation='Stop-Process';commandSucceeded=$true;waitForExit=$wait;actualProcessExitCode=$nativeExit}
}
& $mysqladmin "--defaults-file=$($s.rootConfig)" --skip-password shutdown 2>&1|Set-Content (Join-Path $out 'final-stop-mysqladmin.log') -Encoding utf8
$shutdownExit=$LASTEXITCODE
foreach($mysqlPid in $mysqlPids){
 $proc=$dbHandles[$mysqlPid]
 $wait=$proc.WaitForExit(10000)
 $nativeExit=$null
 if($wait){$nativeExit=$proc.ExitCode}
 $exitRecords+=@{pid=$mysqlPid;operation='mysqladmin shutdown';waitForExit=$wait;actualProcessExitCode=$nativeExit}
}
$remaining=@(Get-CimInstance Win32_Process|Where-Object {$_.ProcessId -in ($appPids+$mysqlPids) -or ($_.Name -eq 'mysqld.exe' -and $_.CommandLine -like "*--datadir=$($s.datadir)*")}|Select-Object ProcessId,ParentProcessId,Name,CommandLine,ExecutablePath)
$remainingListeners=@(Get-NetTCPConnection -State Listen|Where-Object {$_.LocalPort -in @(8080,8081,18080,59315)}|Select-Object LocalAddress,LocalPort,State,OwningProcess)
$result=@{stoppedAt=(Get-Date -Format o);mysqladminExitCode=$shutdownExit;processExits=$exitRecords;remainingReviewProcesses=$remaining;remainingReviewListenerPorts=$remainingListeners;datadirRetained=(Test-Path -LiteralPath $s.datadir);rootDefaultsRetained=(Test-Path -LiteralPath $s.rootConfig);appDefaultsRetained=(Test-Path -LiteralPath $s.appConfig);privateStateRetained=(Test-Path -LiteralPath (Join-Path $s.tempDirectory 'private-state.json'));otherDevelopmentInstancesTouched=$false;result=if($shutdownExit -eq 0 -and $remaining.Count -eq 0 -and $remainingListeners.Count -eq 0){'PASS'}else{'INCOMPLETE'}}
$result|ConvertTo-Json -Depth 7|Set-Content (Join-Path $out 'final-stop-result.json') -Encoding utf8
Add-Content -LiteralPath (Join-Path (Split-Path $out) 'commands-environment.md') -Encoding utf8 -Value '`pwsh -NoProfile -File environment/final-stop.ps1 (SELECT @@port/@@datadir/@@server_uuid; verify PID/command/listener; Stop-Process 37480/3936; mysqladmin --defaults-file=<temporary root.cnf> --skip-password shutdown; read native exit codes and remaining processes/listeners; retain temporary files)`'
Write-Output ('FINAL_STOP_RESULT='+$result.result)
Write-Output ('MYSQLADMIN_EXIT='+$shutdownExit)
