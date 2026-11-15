$ErrorActionPreference = 'Stop'
$verifyRoot = 'C:\Users\Starmetor\.codex\visualizations\2026\11\10\01a1c2de-c7a6-7290-8ee3-510d0f746abe\ui-redesign\verification'
$runtimeRoot = [IO.Path]::GetFullPath((Join-Path $verifyRoot 'runtime'))
$rootPrefix = $runtimeRoot.TrimEnd('\') + '\'
$records = @()
$blocked = @()
$allPorts = [Collections.Generic.HashSet[int]]::new()
$started = [DateTime]::UtcNow.ToString('o')
function Assert-PrivatePath([string]$Path) {
  $absolute = [IO.Path]::GetFullPath($Path)
  if(-not $absolute.StartsWith($rootPrefix,[StringComparison]::OrdinalIgnoreCase)){throw 'Target outside owned runtime root'}
  $cursor = $absolute
  $runtimeItem=Get-Item -LiteralPath $runtimeRoot -Force -ErrorAction Stop
  if(($runtimeItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw 'Runtime root is a reparse point; retained'}
  while($cursor -and -not $cursor.Equals($runtimeRoot,[StringComparison]::OrdinalIgnoreCase)) {
    if(Test-Path -LiteralPath $cursor) {
      $item=Get-Item -LiteralPath $cursor -Force
      if(($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw 'Reparse target is not eligible for automatic deletion'}
    }
    $cursor=[IO.Path]::GetDirectoryName($cursor)
  }
  return $absolute
}
function Has-ExactArgument([string]$Command,[string]$Argument) {
  if(-not $Command){return $false}
  return [regex]::IsMatch($Command,'(?:^|\s)"?'+[regex]::Escape($Argument)+'"?(?:$|\s)',[Text.RegularExpressions.RegexOptions]::IgnoreCase)
}
function Matches-Creation($Process,[DateTimeOffset]$Expected) {
  if(-not $Process -or -not $Process.CreationDate){return $false}
  return [Math]::Abs((([DateTimeOffset]$Process.CreationDate).ToUniversalTime()-$Expected.ToUniversalTime()).TotalSeconds) -le 5
}
foreach($attempt in Get-ChildItem -LiteralPath $runtimeRoot -Directory | Where-Object Name -Match '^attempt[1-9][0-9]*$') {
  $name=$attempt.Name
  $evidence=Join-Path (Join-Path $verifyRoot 'evidence') $name
  $identityPath=Join-Path $evidence 'database-identity.json'
  $row=[ordered]@{attempt=$name;owned_path=$null;uuid=$null;guard_passed=$false;process_checks=@();stopped=$false;deleted=$false;private_configs=@();reason=$null}
  try {
    if(-not (Test-Path -LiteralPath $identityPath)){throw 'No original identity record; retained'}
    $identity=Get-Content -Raw -LiteralPath $identityPath | ConvertFrom-Json
    $expected=Assert-PrivatePath (Join-Path $attempt.FullName 'mysql-data')
    $declared=[IO.Path]::GetFullPath($identity.private_datadir)
    if(-not $expected.Equals($declared,[StringComparison]::OrdinalIgnoreCase)){throw 'Identity datadir differs from expected owned path'}
    $row.owned_path=$expected;$row.uuid=$identity.uuid
    [void]$allPorts.Add([int]$identity.port)
    if(Test-Path -LiteralPath $expected) {
      $actual=(Select-String -LiteralPath (Join-Path $expected 'auto.cnf') -Pattern '^server-uuid=(.+)$').Matches.Groups[1].Value.Trim()
      if($actual -ne $identity.uuid){throw 'Datadir UUID mismatch; retained'}
    }
    $row.guard_passed=$true
    $launchPath=Join-Path $evidence 'launches.jsonl'
    $launches=@(Get-Content -LiteralPath $launchPath | ForEach-Object {$_ | ConvertFrom-Json})
    foreach($launch in $launches) {
      [void]$allPorts.Add([int]$launch.port)
      $proc=Get-CimInstance Win32_Process -Filter "ProcessId=$($launch.pid)" -ErrorAction Stop
      $commandMatches=$null -ne $proc -and $proc.Name -eq 'java.exe' -and (Has-ExactArgument $proc.CommandLine $launch.args[2]) -and (Has-ExactArgument $proc.CommandLine ('--server.port='+$launch.port))
      $creationMatches=Matches-Creation $proc ([DateTimeOffset]::Parse($launch.at))
      if($commandMatches -and -not $creationMatches){throw 'Same-command Java PID has a different creation time; retained'}
      $owned=$commandMatches -and $creationMatches
      $stoppedNow=$false
      if($owned){Stop-Process -Id $launch.pid -Force;Wait-Process -Id $launch.pid -Timeout 10 -ErrorAction SilentlyContinue;$stoppedNow=$true}
      $remaining=Get-CimInstance Win32_Process -Filter "ProcessId=$($launch.pid)" -ErrorAction Stop
      if($remaining -and (Has-ExactArgument $remaining.CommandLine $launch.args[2]) -and (Matches-Creation $remaining ([DateTimeOffset]::Parse($launch.at)))){throw 'Owned Java process remains after stop; retained'}
      $row.process_checks+=@{kind=$launch.app;pid=$launch.pid;found=($null -ne $proc);command_matches_owned=[bool]$commandMatches;creation_matches_owned=[bool]$creationMatches;terminated_now=$stoppedNow;unrelated_pid_reuse_preserved=($null -ne $proc -and -not $owned)}
    }
    $serverLog=Join-Path $attempt.FullName 'mysql-server.log'
    $serverMatch=Select-String -LiteralPath $serverLog -Pattern 'starting as process (\d+)' | Select-Object -First 1
    if(-not $serverMatch){throw 'No original server PID observation; retained'}
    $mysqlPid=[int]$serverMatch.Matches.Groups[1].Value
    $proc=Get-CimInstance Win32_Process -Filter "ProcessId=$mysqlPid" -ErrorAction Stop
    $commandMatches=$null -ne $proc -and $proc.Name -eq 'mysqld.exe' -and (Has-ExactArgument $proc.CommandLine ('--datadir='+$expected))
    $expectedStart=[DateTimeOffset]::Parse(($serverMatch.Line -split '\s+')[0])
    $creationMatches=Matches-Creation $proc $expectedStart
    if($commandMatches -and -not $creationMatches){throw 'Same-command MySQL PID has a different creation time; retained'}
    $owned=$commandMatches -and $creationMatches
    $stoppedNow=$false
    if($owned){Stop-Process -Id $mysqlPid -Force;Wait-Process -Id $mysqlPid -Timeout 10 -ErrorAction SilentlyContinue;$stoppedNow=$true}
    $row.process_checks+=@{kind='mysqld';pid=$mysqlPid;found=($null -ne $proc);command_matches_owned=[bool]$commandMatches;creation_matches_owned=[bool]$creationMatches;terminated_now=$stoppedNow;unrelated_pid_reuse_preserved=($null -ne $proc -and -not $owned)}
    $active=@(Get-CimInstance Win32_Process -Filter "Name='mysqld.exe'" -ErrorAction Stop | Where-Object { Has-ExactArgument $_.CommandLine ('--datadir='+$expected) })
    if($active.Count){throw 'An owned-datadir MySQL process remains; retained'}
    $row.stopped=$true
    if(Test-Path -LiteralPath $expected){
      $checked=Assert-PrivatePath $expected
      $links=@(Get-ChildItem -LiteralPath $checked -Recurse -Force -Attributes ReparsePoint -ErrorAction Stop)
      if($links.Count){throw 'Datadir contains reparse descendants; retained'}
      Remove-Item -LiteralPath $checked -Recurse -Force
    }
    $row.deleted=-not (Test-Path -LiteralPath $expected)
    foreach($file in Get-ChildItem -LiteralPath $attempt.FullName -File -Filter '*-private.sql') {
      $checked=Assert-PrivatePath $file.FullName;Remove-Item -LiteralPath $checked -Force
      $row.private_configs+=@{path=$checked;deleted=(-not (Test-Path -LiteralPath $checked))}
    }
  }catch{$row.reason=$_.Exception.Message;$blocked+=@{attempt=$name;reason=$row.reason}}
  $records+=[pscustomobject]$row
}
$listenerQuerySucceeded=$false;$listeners=@()
try{$listeners=@(Get-NetTCPConnection -State Listen -ErrorAction Stop | Where-Object {$allPorts.Contains([int]$_.LocalPort)} | Select-Object LocalAddress,LocalPort,OwningProcess);$listenerQuerySucceeded=$true}catch{$blocked+=@{attempt='all';reason='Listener query failed; no absence claim'}}
$result=[ordered]@{started_at_utc=$started;finished_at_utc=[DateTime]::UtcNow.ToString('o');scope='Only new UI-redesign verification/runtime attempt datadirs and residual private init SQL; evidence/scripts/original manifests untouched';overall=if($blocked.Count -eq 0 -and @($records|Where-Object {-not $_.deleted}).Count -eq 0 -and $listenerQuerySucceeded -and $listeners.Count -eq 0){'PASS'}else{'RETAINED_UNCONFIRMED'};records=$records;ports_checked=@($allPorts);listener_query_succeeded=$listenerQuerySucceeded;current_matching_listeners=$listeners;blocked=$blocked;secret_values_recorded=$false}
$result | ConvertTo-Json -Depth 9 | Set-Content -LiteralPath (Join-Path $verifyRoot 'cleanup.json') -Encoding utf8
Write-Output ("UI_CLEANUP_"+$result.overall)
if($result.overall -ne 'PASS'){exit 1}
