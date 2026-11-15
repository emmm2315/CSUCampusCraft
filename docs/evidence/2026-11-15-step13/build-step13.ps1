param([ValidateSet('user','admin')][string]$Module)
$ErrorActionPreference='Stop'
$taskStage='C:/Users/Starmetor/.codex/visualizations/2026/11/10/01a1c2de-c7a6-7290-8ee3-510d0f746abe/step13-acceptance'
$env:JAVA_HOME='C:/Users/Starmetor/.jdks/ms-21.0.12.1'
$env:Path="$env:SystemRoot\System32;$env:SystemRoot;$env:SystemRoot\System32\WindowsPowerShell\v1.0"
if($null -ne (Get-Command mvn -ErrorAction SilentlyContinue)){throw 'Maven unexpectedly available on PATH'}
Set-Location -LiteralPath 'D:/Github Projects/CSUCampusCraft'
$taskLog=Join-Path $taskStage ('build-'+$Module+'.log')
$taskStarted=(Get-Date).ToUniversalTime().ToString('o')
& .\mvnw.cmd -o -s 'C:/Users/Starmetor/.codex/visualizations/2026/11/10/01a1c2de-c7a6-7290-8ee3-510d0f746abe/docs-admin-sequence/runtime/settings.xml' '-Dmaven.repo.local=C:/Users/Starmetor/.codex/visualizations/2026/11/10/01a1c2de-c7a6-7290-8ee3-510d0f746abe/docs-admin-sequence/runtime/m2' -f ('csucampuscraft-'+$Module+'/pom.xml') clean verify 2>&1 | Out-File -LiteralPath $taskLog -Encoding utf8
$taskExit=$LASTEXITCODE
@{module=$Module;exit_code=$taskExit;started_at_utc=$taskStarted;finished_at_utc=(Get-Date).ToUniversalTime().ToString('o');maven_absent_from_path=$true;java_home=$env:JAVA_HOME;command=('.\mvnw.cmd -o -s <isolated settings> -Dmaven.repo.local=<isolated cache> -f csucampuscraft-'+$Module+'/pom.xml clean verify')} | ConvertTo-Json | Out-File -LiteralPath (Join-Path $taskStage ('build-'+$Module+'.json')) -Encoding utf8
Get-Content -Tail 8 -LiteralPath $taskLog
exit $taskExit
