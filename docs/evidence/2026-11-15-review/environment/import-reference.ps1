$ErrorActionPreference='Stop'
$repo='D:\Github Projects\CSUCampusCraft'
Set-Location -LiteralPath $repo
$out=Join-Path $repo 'docs\evidence\2026-11-15-review\environment'
$s=Get-Content (Join-Path $out 'state.json') -Raw | ConvertFrom-Json
$mysql='D:\MySQL\bin\mysql.exe'
$target=@(& $mysql "--defaults-file=$($s.rootConfig)" --skip-password --batch --raw --skip-column-names --execute='SELECT @@port,@@datadir,@@server_uuid;')
if($LASTEXITCODE -ne 0){throw '无法确认隔离实例'}
$fields=$target[0] -split "`t"
$normalize={param([string]$p) ($p -replace '\\','/').TrimEnd('/')}
if([int]$fields[0] -ne $s.dbPort -or (& $normalize $fields[1]) -ne (& $normalize $s.datadir)){throw '连接未指向本轮隔离实例；拒绝建库'}
$target | Set-Content (Join-Path $out 'reference-target.tsv') -Encoding utf8
$sql='CREATE DATABASE review_reference CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_as_ci;'
$sql | Set-Content (Join-Path $out 'reference-create.sql') -Encoding utf8
& $mysql "--defaults-file=$($s.rootConfig)" --skip-password "--execute=$sql" 2>&1 | Set-Content (Join-Path $out 'reference-create.log') -Encoding utf8
$createExit=$LASTEXITCODE
if($createExit -ne 0){throw '创建reference库失败'}
& $mysql "--defaults-file=$($s.rootConfig)" --skip-password --database=review_reference --execute='SOURCE database/02-schema-with-demo.sql' 2>&1 | Set-Content (Join-Path $out 'reference-import.log') -Encoding utf8
$importExit=$LASTEXITCODE
if($importExit -ne 0){throw '导入reference失败'}
$countsSql=Get-Content (Join-Path $out 'counts.sql') -Raw
& $mysql "--defaults-file=$($s.rootConfig)" --skip-password --database=review_reference --batch "--execute=$countsSql" 2>&1 | Set-Content (Join-Path $out 'reference-counts.tsv') -Encoding utf8
$countsExit=$LASTEXITCODE
@{createdAt=(Get-Date -Format o);schema='review_reference';createExitCode=$createExit;importExitCode=$importExit;countsExitCode=$countsExit;source='database/02-schema-with-demo.sql';sourceSha256=(Get-FileHash database/02-schema-with-demo.sql -Algorithm SHA256).Hash.ToLowerInvariant();dbPort=$s.dbPort;serverUuid=$fields[2];datadirVerified=$true} | ConvertTo-Json -Depth 4 | Set-Content (Join-Path $out 'reference-result.json') -Encoding utf8
Add-Content -LiteralPath (Join-Path (Split-Path $out) 'commands-environment.md') -Encoding utf8 -Value '`pwsh -NoProfile -File environment/import-reference.ps1 (verify @@port/@@datadir, CREATE DATABASE review_reference, mysql --database=review_reference --execute="SOURCE database/02-schema-with-demo.sql", seven-table counts)`'
Write-Output ('REFERENCE_IMPORT_EXIT='+$importExit)
