$ErrorActionPreference='Stop'
$out='D:\Github Projects\CSUCampusCraft\docs\evidence\2026-11-15-review\environment'
$s=Get-Content (Join-Path $out 'short-ttl-state.json') -Raw | ConvertFrom-Json
$p=Get-CimInstance Win32_Process -Filter "ProcessId = $($s.pid)"
if ($null -eq $p) { throw '辅助 PID 已不存在；不对其他进程操作。' }
if ($p.Name -ne 'java.exe' -or $p.CommandLine -notlike '*-jar csucampuscraft-user/target/csucampuscraft-user-0.0.1-SNAPSHOT.jar --server.port=18080 --csucampuscraft.checkout.confirmation-ttl=PT2S*') { throw '辅助 PID 归属不匹配；停止。' }
$listeners=@(Get-NetTCPConnection -LocalPort 18080 -State Listen -ErrorAction SilentlyContinue)
if ($listeners.Count -eq 0 -or @($listeners | Where-Object {$_.OwningProcess -ne $s.pid}).Count -ne 0) { throw '18080 监听归属不匹配；停止。' }
$before=$p|Select-Object ProcessId,ParentProcessId,Name,CommandLine,ExecutablePath,CreationDate
Stop-Process -Id $s.pid
for($i=0;$i -lt 20;$i++) { if ($null -eq (Get-Process -Id $s.pid -ErrorAction SilentlyContinue)) {break};Start-Sleep -Milliseconds 100 }
$afterProcess=@(Get-Process -Id $s.pid -ErrorAction SilentlyContinue).Count
$afterListener=@(Get-NetTCPConnection -LocalPort 18080 -State Listen -ErrorAction SilentlyContinue).Count
$result=@{stoppedAt=(Get-Date -Format o);before=$before;afterProcessCount=$afterProcess;afterListenerCount=$afterListener;onlyPidStopped=$s.pid;mainProcessesRetained=$true}
$result | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $out 'short-ttl-stop-result.json') -Encoding utf8
Add-Content -LiteralPath (Join-Path (Split-Path $out) 'commands-environment.md') -Encoding utf8 -Value '`pwsh -NoProfile -File environment/stop-short-ttl.ps1 (verify PID2276 command and 18080 listener; Stop-Process -Id 2276)`'
Write-Output ('SHORT_TTL_STOPPED=' + ($afterProcess -eq 0 -and $afterListener -eq 0))
