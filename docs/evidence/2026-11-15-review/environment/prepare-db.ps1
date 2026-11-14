$ErrorActionPreference = 'Stop'
$repo = 'D:\Github Projects\CSUCampusCraft'
$out = Join-Path $repo 'docs\evidence\2026-11-15-review\environment'
Set-Location -LiteralPath $repo
$env:JAVA_HOME = 'C:\Users\Starmetor\.jdks\ms-21.0.12.1'
$commands = Join-Path (Split-Path $out) 'commands-environment.md'
function Note([string]$command) { Add-Content -LiteralPath $commands -Value ('`' + $command + '`') -Encoding utf8 }
$tmp = Join-Path ([IO.Path]::GetTempPath()) ('csucampuscraft-review-20261115-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $tmp | Out-Null
$data = Join-Path $tmp 'data'
$port = 59315
$bound = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback,$port)
$bound.Start(); $bound.Stop()
Note "D:\MySQL\bin\mysqld.exe --no-defaults --initialize-insecure --basedir=D:\MySQL --datadir=$data --console"
& D:\MySQL\bin\mysqld.exe --no-defaults --initialize-insecure --basedir=D:\MySQL "--datadir=$data" --console 2>&1 | Set-Content -LiteralPath (Join-Path $out 'mysql-initialize-attempt2.log') -Encoding utf8
$initExit = $LASTEXITCODE
if ($initExit -ne 0) { throw "MySQL initialize exit=$initExit" }
$mysqlArgs = @('--no-defaults','--basedir=D:\MySQL',"--datadir=$data",'--bind-address=127.0.0.1',"--port=$port",'--mysqlx=0','--default-time-zone=+00:00','--console')
Note ('Start-Process -FilePath D:\MySQL\bin\mysqld.exe -ArgumentList ' + ($mysqlArgs -join ' ') + ' -WindowStyle Hidden -PassThru (stdout/stderr archived)')
$db = Start-Process -FilePath 'D:\MySQL\bin\mysqld.exe' -ArgumentList $mysqlArgs -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $out 'mysql.stdout.log') -RedirectStandardError (Join-Path $out 'mysql.stderr.log')
$rootConfig = Join-Path $tmp 'root.cnf'
"[client]`nhost=127.0.0.1`nport=$port`nuser=root`nprotocol=tcp`ndefault-character-set=utf8mb4`n" | Set-Content -LiteralPath $rootConfig -Encoding utf8NoBOM
for ($i=0; $i -lt 60; $i++) {
  $ping = & D:\MySQL\bin\mysql.exe "--defaults-file=$rootConfig" --skip-password -N -e 'SELECT 1' 2>&1
  if ($LASTEXITCODE -eq 0) { break }
  Start-Sleep -Milliseconds 500
}
$password = [guid]::NewGuid().ToString('N')
$sql = "CREATE DATABASE csucampuscraft CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_as_ci; CREATE DATABASE review_schema CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_as_ci; CREATE USER 'review_app'@'127.0.0.1' IDENTIFIED BY '$password'; GRANT SELECT,INSERT,UPDATE,DELETE ON csucampuscraft.* TO 'review_app'@'127.0.0.1';"
Note 'mysql --defaults-file=<temporary root.cnf> --skip-password (stdin CREATE DATABASE csucampuscraft/review_schema; CREATE USER review_app; GRANT SELECT,INSERT,UPDATE,DELETE; random password omitted)'
$sql | & D:\MySQL\bin\mysql.exe "--defaults-file=$rootConfig" --skip-password 2>&1 | Set-Content -LiteralPath (Join-Path $out 'mysql-create.log') -Encoding utf8
if ($LASTEXITCODE -ne 0) { throw '建库/授权失败' }
Note 'mysql --defaults-file=<temporary root.cnf> --skip-password --database=csucampuscraft --execute="SOURCE database/02-schema-with-demo.sql"'
& D:\MySQL\bin\mysql.exe "--defaults-file=$rootConfig" --skip-password --database=csucampuscraft --execute='SOURCE database/02-schema-with-demo.sql' 2>&1 | Set-Content -LiteralPath (Join-Path $out 'import-demo.log') -Encoding utf8
$demoExit = $LASTEXITCODE
if ($demoExit -ne 0) { throw '演示SQL导入失败' }
Note 'mysql --defaults-file=<temporary root.cnf> --skip-password --database=review_schema --execute="SOURCE database/01-schema.sql"'
& D:\MySQL\bin\mysql.exe "--defaults-file=$rootConfig" --skip-password --database=review_schema --execute='SOURCE database/01-schema.sql' 2>&1 | Set-Content -LiteralPath (Join-Path $out 'import-schema.log') -Encoding utf8
$schemaExit = $LASTEXITCODE
if ($schemaExit -ne 0) { throw '结构SQL导入失败' }
$appConfig = Join-Path $tmp 'app.cnf'
"[client]`nhost=127.0.0.1`nport=$port`nuser=review_app`npassword=$password`nprotocol=tcp`ndefault-character-set=utf8mb4`n" | Set-Content -LiteralPath $appConfig -Encoding utf8NoBOM
$countsSql = "SELECT 'store_user',COUNT(*) FROM store_user UNION ALL SELECT 'category',COUNT(*) FROM category UNION ALL SELECT 'product',COUNT(*) FROM product UNION ALL SELECT 'product_image',COUNT(*) FROM product_image UNION ALL SELECT 'cart_item',COUNT(*) FROM cart_item UNION ALL SELECT 'sales_order',COUNT(*) FROM sales_order UNION ALL SELECT 'sales_order_item',COUNT(*) FROM sales_order_item;"
$countsSql | Set-Content -LiteralPath (Join-Path $out 'counts.sql') -Encoding utf8NoBOM
foreach ($schema in @('csucampuscraft','review_schema')) {
  Note "mysql --defaults-file=<temporary root.cnf> --skip-password --database=$schema --batch --execute=<counts.sql>"
  & D:\MySQL\bin\mysql.exe "--defaults-file=$rootConfig" --skip-password "--database=$schema" --batch "--execute=$countsSql" | Set-Content -LiteralPath (Join-Path $out "$schema-counts.tsv") -Encoding utf8
}
$env:CSUCAMPUSCRAFT_DB_URL = "jdbc:mysql://127.0.0.1:$port/csucampuscraft"
$env:CSUCAMPUSCRAFT_DB_USER = 'review_app'
$env:CSUCAMPUSCRAFT_DB_PASSWORD = $password
$pids = @{}
foreach ($side in @('user','admin')) {
  $jar = "csucampuscraft-$side/target/csucampuscraft-$side-0.0.1-SNAPSHOT.jar"
  Note "Start-Process -FilePath $env:JAVA_HOME\bin\java.exe -ArgumentList '-jar',$jar -WindowStyle Hidden -PassThru (CSUCAMPUSCRAFT_DB_URL/USER/PASSWORD inherited)"
  $app = Start-Process -FilePath "$env:JAVA_HOME\bin\java.exe" -ArgumentList @('-jar',$jar) -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $out "app-$side.stdout.log") -RedirectStandardError (Join-Path $out "app-$side.stderr.log")
  $pids[$side] = $app.Id
}
$state = @{ tempDirectory=$tmp; datadir=$data; dbPort=$port; mysqlPid=$db.Id; userPid=$pids.user; adminPid=$pids.admin; userPort=8080; adminPort=8081; dbUrl=$env:CSUCAMPUSCRAFT_DB_URL; dbUser=$env:CSUCAMPUSCRAFT_DB_USER; rootConfig=$rootConfig; appConfig=$appConfig; initializeExit=$initExit; demoImportExit=$demoExit; schemaImportExit=$schemaExit; createdAt=(Get-Date -Format o) }
$state | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $out 'state.json') -Encoding utf8
@{password=$password; state=$state} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $tmp 'private-state.json') -Encoding utf8
Write-Output ('READY_STATE=' + (Join-Path $out 'state.json'))
