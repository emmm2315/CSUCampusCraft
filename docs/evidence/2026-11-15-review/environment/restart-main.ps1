$ErrorActionPreference='Stop'
$repo='D:\Github Projects\CSUCampusCraft'
Set-Location -LiteralPath $repo
$out=Join-Path $repo 'docs\evidence\2026-11-15-review\environment'
$s=Get-Content (Join-Path $out 'state.json') -Raw | ConvertFrom-Json
$private=Get-Content (Join-Path $s.tempDirectory 'private-state.json') -Raw | ConvertFrom-Json
$connPath=Join-Path ([IO.Path]::GetTempPath()) 'review-connection.json'
$conn=Get-Content $connPath -Raw | ConvertFrom-Json
$priorHashes=Get-Content (Join-Path $out 'inspection-result.json') -Raw | ConvertFrom-Json
$java='C:\Users\Starmetor\.jdks\ms-21.0.12.1\bin\java.exe'
$records=@()
foreach($side in @('user','admin')) {
  $priorPid=if($side -eq 'user'){$conn.user_pid}else{$conn.admin_pid}
  $port=if($side -eq 'user'){8080}else{8081}
  $jar="csucampuscraft-$side/target/csucampuscraft-$side-0.0.1-SNAPSHOT.jar"
  $process=Get-CimInstance Win32_Process -Filter "ProcessId = $priorPid"
  if($null -eq $process -or $process.Name -ne 'java.exe' -or $process.ExecutablePath -ne $java -or $process.CommandLine -notlike "*-jar $jar") {throw "进程归属不符 $side；拒绝重启"}
  $listeners=@(Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)
  if($listeners.Count -eq 0 -or @($listeners|Where-Object {$_.OwningProcess -ne $priorPid}).Count -ne 0){throw "端口归属不符 $side；拒绝重启"}
  $hash=(Get-FileHash -LiteralPath (Join-Path $repo $jar) -Algorithm SHA256).Hash.ToLowerInvariant()
  if($hash -ne $priorHashes.jars.$side.sha256){throw "JAR与本轮构建基线不符 $side"}
  $records+= [pscustomobject]@{side=$side;oldPid=$priorPid;port=$port;jar=$jar;sha256=$hash;before=($process|Select-Object ProcessId,ParentProcessId,Name,CommandLine,ExecutablePath,CreationDate);stopSucceeded=$false;newPid=$null;running=$false;processExitCode=$null;listenerOwned=$false}
}
$records|ConvertTo-Json -Depth 6 | Set-Content (Join-Path $out 'restart1-before.json') -Encoding utf8
foreach($record in $records) {
  Stop-Process -Id $record.oldPid
  for($i=0;$i -lt 30;$i++){if($null -eq (Get-Process -Id $record.oldPid -ErrorAction SilentlyContinue)){break};Start-Sleep -Milliseconds 100}
  $record.stopSucceeded=($null -eq (Get-Process -Id $record.oldPid -ErrorAction SilentlyContinue))
  if(-not $record.stopSucceeded){throw "旧PID未停止 $($record.oldPid)"}
}
$env:CSUCAMPUSCRAFT_DB_URL=$s.dbUrl
$env:CSUCAMPUSCRAFT_DB_USER=$s.dbUser
$env:CSUCAMPUSCRAFT_DB_PASSWORD=$private.password
foreach($record in $records){
  $app=Start-Process -FilePath $java -ArgumentList @('-jar',$record.jar) -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $out "restart1-$($record.side).stdout.log") -RedirectStandardError (Join-Path $out "restart1-$($record.side).stderr.log")
  $record.newPid=$app.Id
}
for($i=0;$i -lt 60;$i++){
  foreach($record in $records){
    $record.running=($null -ne (Get-Process -Id $record.newPid -ErrorAction SilentlyContinue))
    $record.listenerOwned=(@(Get-NetTCPConnection -LocalPort $record.port -State Listen -ErrorAction SilentlyContinue | Where-Object {$_.OwningProcess -eq $record.newPid}).Count -gt 0)
  }
  if(@($records|Where-Object {-not $_.listenerOwned}).Count -eq 0){break}
  Start-Sleep -Milliseconds 250
}
foreach($record in $records){if(-not $record.running -or -not $record.listenerOwned){throw "新实例未就绪 $($record.side)"}}
$conn.user_pid=($records|Where-Object side -eq 'user').newPid
$conn.admin_pid=($records|Where-Object side -eq 'admin').newPid
$conn|ConvertTo-Json -Depth 5|Set-Content $connPath -Encoding utf8
@{restartedAt=(Get-Date -Format o);records=$records;dbUrl=$s.dbUrl;mysqlRetained=$true;databaseWritesIssuedByThisScript=$false;exitNote='Start-Process applications remain running; processExitCode is null, not an inferred zero.'}|ConvertTo-Json -Depth 7|Set-Content (Join-Path $out 'restart1-result.json') -Encoding utf8
Add-Content -LiteralPath (Join-Path (Split-Path $out) 'commands-environment.md') -Encoding utf8 -Value '`pwsh -NoProfile -File environment/restart-main.ps1 (verify old PIDs/JAR SHA/listeners, Stop-Process old main PIDs, Start-Process same JAR/environment -WindowStyle Hidden, confirm new listeners, update temporary connection PIDs; no DB writes)`'
Write-Output ('USER_NEW_PID='+$conn.user_pid)
Write-Output ('ADMIN_NEW_PID='+$conn.admin_pid)
