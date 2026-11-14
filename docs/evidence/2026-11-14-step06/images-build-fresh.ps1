param([string]$Module)
$ErrorActionPreference='Stop'
$env:JAVA_HOME='C:/Users/Starmetor/.jdks/ms-21.0.12.1'
$env:Path="$env:SystemRoot\System32;$env:SystemRoot;$env:SystemRoot\System32\WindowsPowerShell\v1.0"
$taskMissingMaven=($null -eq (Get-Command mvn -ErrorAction SilentlyContinue))
if(-not $taskMissingMaven){throw 'Maven must be absent from child PATH'}
Set-Location -LiteralPath 'D:/Github Projects/CSUCampusCraft'
$taskLog='C:/Users/Starmetor/.codex/visualizations/2026/11/10/01a1c2de-c7a6-7290-8ee3-510d0f746abe/step06-admin-images/build-'+$Module+'.log'
& .\mvnw.cmd -o -s 'C:/Users/Starmetor/.codex/visualizations/2026/11/10/01a1c2de-c7a6-7290-8ee3-510d0f746abe/docs-admin-sequence/runtime/settings.xml' '-Dmaven.repo.local=C:/Users/Starmetor/.codex/visualizations/2026/11/10/01a1c2de-c7a6-7290-8ee3-510d0f746abe/docs-admin-sequence/runtime/m2' -f ('csucampuscraft-'+$Module+'/pom.xml') verify 2>&1 | Out-File -LiteralPath $taskLog -Encoding utf8
$taskExit=$LASTEXITCODE
@{module=$Module;exit_code=$taskExit;maven_absent_from_path=$taskMissingMaven;java_home=$env:JAVA_HOME;command=('.\mvnw.cmd -o -s <isolated settings> -Dmaven.repo.local=<isolated cache> -f csucampuscraft-'+$Module+'/pom.xml verify')} | ConvertTo-Json | Out-File -LiteralPath ('C:/Users/Starmetor/.codex/visualizations/2026/11/10/01a1c2de-c7a6-7290-8ee3-510d0f746abe/step06-admin-images/build-'+$Module+'.json') -Encoding utf8
Get-Content -Tail 6 -LiteralPath $taskLog
exit $taskExit

