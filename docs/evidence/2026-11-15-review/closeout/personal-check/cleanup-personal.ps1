param([switch]$ConfirmedHumanSessionComplete)
$ErrorActionPreference='Stop'
if(-not $ConfirmedHumanSessionComplete){throw 'Cleanup is prepared only. Run after the human session and result/name confirmation have ended.'}
$repo='D:\Github Projects\CSUCampusCraft'
$out=Join-Path $repo 'docs\evidence\2026-11-15-review\closeout\personal-check'
$state=Get-Content -LiteralPath (Join-Path $out 'state.json') -Raw|ConvertFrom-Json -AsHashtable
$baseRoot=[IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\')
$target=[IO.Path]::GetFullPath([string]$state.tempDirectory).TrimEnd('\')
if([IO.Path]::GetDirectoryName($target) -ne $baseRoot -or [IO.Path]::GetFileName($target) -notmatch '^csucampuscraft-personal-20261115-[0-9a-f]{32}$'){throw 'Temporary directory is outside exact approved per-session root'}
$resolved=(Resolve-Path -LiteralPath $target).Path.TrimEnd('\')
if($resolved -ne $target -or [IO.Path]::GetFullPath([string]$state.datadir).TrimEnd('\') -ne (Join-Path $target 'data')){throw 'Resolved cleanup target mismatch'}
if((Get-Item -LiteralPath $target).Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Refuse cleanup through reparse point'}
$mysql='D:\MySQL\bin\mysql.exe';$mysqladmin='D:\MySQL\bin\mysqladmin.exe'
$identity=@(& $mysql "--defaults-file=$($state.rootConfig)" --skip-password --batch --raw --skip-column-names --execute='SELECT @@port,@@datadir,@@server_uuid;')
$identityExit=$LASTEXITCODE
if($identityExit -ne 0){throw 'Cannot verify currently running isolated DB target'}
$f=$identity[0]-split "`t";$normalize={param([string]$p)($p-replace '\\','/').TrimEnd('/')}
if([int]$f[0] -ne $state.dbPort -or (& $normalize $f[1]) -ne (& $normalize $state.datadir) -or $f[2] -ne $state.serverUuid){throw 'Database port/datadir/UUID mismatch; no process stopped'}
$all=@(Get-CimInstance Win32_Process)
$ids=@([int]$state.userPid,[int]$state.adminPid,[int]$state.mysqlStartedPid,[int]$state.mysqlListeningPid)|Select-Object -Unique
$before=@($all|Where-Object {$_.ProcessId -in $ids}|Select-Object ProcessId,ParentProcessId,Name,CommandLine,ExecutablePath,CreationDate)
foreach($side in @('user','admin')){
 $appId=if($side -eq 'user'){$state.userPid}else{$state.adminPid};$port=if($side -eq 'user'){$state.userPort}else{$state.adminPort}
 $proc=@($before|Where-Object {$_.ProcessId -eq $appId})
 if($proc.Count -ne 1 -or $proc[0].Name -ne 'java.exe' -or $proc[0].CommandLine -notlike "*-jar csucampuscraft-$side/target/csucampuscraft-$side-0.0.1-SNAPSHOT.jar*"){throw 'Java ownership changed; refuse stop'}
 $listen=@(Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction Stop)
 if(@($listen|Where-Object {$_.OwningProcess -ne $appId}).Count -ne 0){throw 'HTTP listener ownership changed'}
}
foreach($dbId in @([int]$state.mysqlStartedPid,[int]$state.mysqlListeningPid)|Select-Object -Unique){
 $proc=@($before|Where-Object {$_.ProcessId -eq $dbId})
 if($proc.Count -ne 1 -or $proc[0].Name -ne 'mysqld.exe' -or $proc[0].CommandLine -notlike "*--datadir=$($state.datadir)*"){throw 'MySQL ownership changed; refuse shutdown'}
}
@{at=(Get-Date -Format o);verifiedTarget=$target;databaseIdentity=$identity;processes=$before;humanCompletionFlag=$true}|ConvertTo-Json -Depth 8|Set-Content -LiteralPath (Join-Path $out 'cleanup-before.json') -Encoding utf8
# Preserve server log before removing this task's temporary data directory.
Get-ChildItem -LiteralPath $state.datadir -Filter '*.err' -File -ErrorAction SilentlyContinue|ForEach-Object {Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $out ('cleanup-preserved-'+$_.Name))}
$exits=@();$handles=@{}
foreach($id in $ids){$process=Get-Process -Id $id;$null=$process.Handle;$handles[$id]=$process}
foreach($appId in @([int]$state.userPid,[int]$state.adminPid)){
 Stop-Process -Id $appId;$wait=$handles[$appId].WaitForExit(10000)
 $exits+=@{pid=$appId;operation='Stop-Process';waitForExit=$wait;actualProcessExitCode=if($wait){$handles[$appId].ExitCode}else{$null}}
}
& $mysqladmin "--defaults-file=$($state.rootConfig)" --skip-password shutdown 2>&1|Set-Content -LiteralPath (Join-Path $out 'cleanup-mysqladmin.log') -Encoding utf8
$shutdownExit=$LASTEXITCODE
foreach($dbId in @([int]$state.mysqlStartedPid,[int]$state.mysqlListeningPid)|Select-Object -Unique){
 $wait=$handles[$dbId].WaitForExit(10000)
 $exits+=@{pid=$dbId;operation='mysqladmin shutdown';waitForExit=$wait;actualProcessExitCode=if($wait){$handles[$dbId].ExitCode}else{$null}}
}
$remaining=@(Get-CimInstance Win32_Process|Where-Object {$_.ProcessId -in $ids -or ($_.Name -eq 'mysqld.exe' -and $_.CommandLine -like "*--datadir=$($state.datadir)*")}|Select-Object ProcessId,Name,CommandLine)
$listeners=@(Get-NetTCPConnection -State Listen|Where-Object {$_.OwningProcess -in $ids}|Select-Object LocalAddress,LocalPort,OwningProcess)
$result=@{at=(Get-Date -Format o);mysqladminExitCode=$shutdownExit;processExits=$exits;remainingReviewProcesses=$remaining;remainingOwnedListeners=$listeners;tempDirectory=$target;targetResolvedVerified=$true;temporaryDirectoryDeleted=$false;otherInstancesTouched=$false}
if($shutdownExit -ne 0 -or $remaining.Count -ne 0 -or $listeners.Count -ne 0){$result.result='INCOMPLETE';$result|ConvertTo-Json -Depth 8|Set-Content -LiteralPath (Join-Path $out 'cleanup-result.json') -Encoding utf8;throw 'Services not fully stopped; no directory deletion performed'}
# Revalidate the literal absolute target immediately before recursive deletion, one shell end-to-end.
if([IO.Path]::GetFullPath((Resolve-Path -LiteralPath $target).Path).TrimEnd('\') -ne $target){throw 'Final cleanup target mismatch'}
Remove-Item -LiteralPath $target -Recurse -Force
$result.temporaryDirectoryDeleted=-not(Test-Path -LiteralPath $target)
$pointer=Join-Path ([IO.Path]::GetTempPath()) 'personal-check-connection.json'
if(Test-Path -LiteralPath $pointer){$p=Get-Content -LiteralPath $pointer -Raw|ConvertFrom-Json;if($p.temp_directory -eq $target){Remove-Item -LiteralPath $pointer -Force}}
$result.result=if($result.temporaryDirectoryDeleted){'PASS'}else{'INCOMPLETE'}
$result|ConvertTo-Json -Depth 8|Set-Content -LiteralPath (Join-Path $out 'cleanup-result.json') -Encoding utf8
Write-Output ('PERSONAL_CLEANUP='+$result.result)
