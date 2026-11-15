$ErrorActionPreference = 'Stop'
$repo = 'D:\Github Projects\CSUCampusCraft'
$out = Join-Path $repo 'docs\evidence\2026-11-15-review\closeout\personal-check'
Set-Location -LiteralPath $repo
if ((git branch --show-current) -ne 'fix/review-closeout') { throw 'Wrong branch; no setup performed' }
if ((git rev-parse HEAD) -ne 'd9ed79c1546128beb8b5924e01f55970b44fa767') { throw 'Unexpected HEAD; no setup performed' }
if (Test-Path -LiteralPath (Join-Path $out 'state.json')) { throw 'This setup has already run; refuse to reuse its instance' }
$env:JAVA_HOME = 'C:\Users\Starmetor\.jdks\ms-21.0.12.1'
$mysqlExe = 'D:\MySQL\bin\mysql.exe'
$mysqldExe = 'D:\MySQL\bin\mysqld.exe'
$caseTemp = Join-Path ([IO.Path]::GetTempPath()) ('csucampuscraft-personal-20261115-' + [guid]::NewGuid().ToString('N'))
$dataDir = Join-Path $caseTemp 'data'
$dbName = 'csucampuscraft_personal_20261115'
$dbUser = 'personal_check_app'
$password = [guid]::NewGuid().ToString('N')
New-Item -ItemType Directory -Path $caseTemp | Out-Null
function Save-Json([string]$name, $value) {
  $value | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath (Join-Path $out $name) -Encoding utf8
}
function Free-Port([int]$port) {
  $probe = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback, $port)
  try { $probe.Start(); return $true } catch { return $false } finally { $probe.Stop() }
}
$reserved = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback, 0)
$reserved.Start(); $dbPort = ([Net.IPEndPoint]$reserved.LocalEndpoint).Port; $reserved.Stop()
if ((Free-Port 8080) -and (Free-Port 8081)) { $userPort = 8080; $adminPort = 8081 }
elseif ((Free-Port 18080) -and (Free-Port 18081)) { $userPort = 18080; $adminPort = 18081 }
else { throw 'Neither authorized HTTP port pair is free; no foreign process stopped' }
$rootConfig = Join-Path $caseTemp 'root.cnf'
$appConfig = Join-Path $caseTemp 'app.cnf'
"[client]`nhost=127.0.0.1`nport=$dbPort`nuser=root`nprotocol=tcp`ndefault-character-set=utf8mb4`n" | Set-Content -LiteralPath $rootConfig -Encoding utf8NoBOM
"[client]`nhost=127.0.0.1`nport=$dbPort`nuser=$dbUser`npassword=$password`nprotocol=tcp`ndefault-character-set=utf8mb4`n" | Set-Content -LiteralPath $appConfig -Encoding utf8NoBOM
$state = [ordered]@{createdAt=(Get-Date -Format o); executor='Codex AI environment preparation only'; humanStepsStarted=$false; branch='fix/review-closeout'; sourceSha='d9ed79c1546128beb8b5924e01f55970b44fa767'; tempDirectory=$caseTemp; datadir=$dataDir; database=$dbName; dbPort=$dbPort; dbUser=$dbUser; rootConfig=$rootConfig; appConfig=$appConfig; userPort=$userPort; adminPort=$adminPort; userUrl="http://127.0.0.1:$userPort"; adminUrl="http://127.0.0.1:$adminPort"; mysqlStartedPid=$null; mysqlListeningPid=$null; userPid=$null; adminPid=$null; serverUuid=$null; phase='initialized setup metadata'}
Save-Json 'state.json' $state
@{password=$password;state=$state} | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath (Join-Path $caseTemp 'private-state.json') -Encoding utf8
try {
  & $mysqldExe --no-defaults --initialize-insecure --basedir=D:\MySQL "--datadir=$dataDir" --console 2>&1 | Set-Content -LiteralPath (Join-Path $out 'mysql-initialize.log') -Encoding utf8
  $state.initializeExitCode=$LASTEXITCODE
  if ($state.initializeExitCode -ne 0) { throw "MySQL initialize exit $($state.initializeExitCode)" }
  $dbArgs=@('--no-defaults','--basedir=D:\MySQL',"--datadir=$dataDir",'--bind-address=127.0.0.1',"--port=$dbPort",'--mysqlx=0','--default-time-zone=+00:00','--console')
  $mysqlProcess=Start-Process -FilePath $mysqldExe -ArgumentList $dbArgs -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $out 'mysql.stdout.log') -RedirectStandardError (Join-Path $out 'mysql.stderr.log')
  $state.mysqlStartedPid=$mysqlProcess.Id; Save-Json 'state.json' $state
  $ready=$false
  for($i=0;$i -lt 60;$i++) {
    $null=& $mysqlExe "--defaults-file=$rootConfig" --skip-password -N --execute='SELECT 1' 2>$null
    if($LASTEXITCODE -eq 0){$ready=$true;break}; Start-Sleep -Milliseconds 500
  }
  if(-not $ready){throw 'New isolated MySQL did not become ready'}
  $target=@(& $mysqlExe "--defaults-file=$rootConfig" --skip-password --batch --raw --skip-column-names --execute='SELECT @@port,@@datadir,@@server_uuid,@@version,@@session.time_zone;')
  $state.targetExitCode=$LASTEXITCODE
  if($state.targetExitCode -ne 0){throw 'Cannot confirm new MySQL identity'}
  $fields=$target[0] -split "`t"
  $normalize={param([string]$path) ($path -replace '\\','/').TrimEnd('/')}
  if([int]$fields[0] -ne $dbPort -or (& $normalize $fields[1]) -ne (& $normalize $dataDir)){throw 'New MySQL target mismatch'}
  $state.serverUuid=$fields[2];$state.mysqlVersion=$fields[3]
  Save-Json 'database-identity.json' @{query='SELECT @@port,@@datadir,@@server_uuid,@@version,@@session.time_zone';exitCode=$state.targetExitCode;port=$dbPort;datadir=$fields[1];serverUuid=$fields[2];version=$fields[3];sessionTimeZone=$fields[4];newDirectory=$true}
  "CREATE DATABASE $dbName CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_as_ci; CREATE USER '$dbUser'@'127.0.0.1' IDENTIFIED BY '$password'; GRANT SELECT,INSERT,UPDATE,DELETE ON $dbName.* TO '$dbUser'@'127.0.0.1';" | & $mysqlExe "--defaults-file=$rootConfig" --skip-password 2>&1 | Set-Content -LiteralPath (Join-Path $out 'create-database.log') -Encoding utf8
  $state.createExitCode=$LASTEXITCODE
  if($state.createExitCode -ne 0){throw 'New empty schema/account creation failed'}
  & $mysqlExe "--defaults-file=$rootConfig" --skip-password "--database=$dbName" --execute='SOURCE database/02-schema-with-demo.sql' 2>&1 | Set-Content -LiteralPath (Join-Path $out 'import-demo.log') -Encoding utf8
  $state.importExitCode=$LASTEXITCODE
  if($state.importExitCode -ne 0){throw 'New demo import failed'}
  $counts="SELECT 'store_user' AS table_name,COUNT(*) AS row_count FROM store_user UNION ALL SELECT 'category',COUNT(*) FROM category UNION ALL SELECT 'product',COUNT(*) FROM product UNION ALL SELECT 'product_image',COUNT(*) FROM product_image UNION ALL SELECT 'cart_item',COUNT(*) FROM cart_item UNION ALL SELECT 'sales_order',COUNT(*) FROM sales_order UNION ALL SELECT 'sales_order_item',COUNT(*) FROM sales_order_item;"
  $countLines=@(& $mysqlExe "--defaults-file=$rootConfig" --skip-password "--database=$dbName" --batch --raw "--execute=$counts")
  $state.countsExitCode=$LASTEXITCODE; $countLines | Set-Content -LiteralPath (Join-Path $out 'initial-counts.tsv') -Encoding utf8
  $countRows=@($countLines | ConvertFrom-Csv -Delimiter "`t")
  if($state.countsExitCode -ne 0 -or (($countRows.row_count -join '/') -ne '4/15/60/100/10/10/20')){throw 'Initial seed counts are not expected'}
  $fixture=@'
SET time_zone='+00:00';
START TRANSACTION;
DELETE ci FROM cart_item ci JOIN store_user u ON u.id=ci.user_id WHERE u.username='alice';
INSERT INTO cart_item(user_id,product_id,quantity,version)
SELECT u.id,p.id,CASE p.sku WHEN 'CSU-LMK-NOTE-01' THEN 2 ELSE 1 END,0
FROM store_user u CROSS JOIN product p
WHERE u.username='alice' AND p.sku IN ('CSU-LMK-NOTE-01','CSU-GRAD-BOX-01');
COMMIT;
SELECT ci.id AS cart_item_id,u.username,p.id AS product_id,p.sku,ci.quantity,ci.version AS cart_version,p.version AS product_version,p.price,p.stock,p.status,p.price*ci.quantity AS subtotal
FROM cart_item ci JOIN store_user u ON u.id=ci.user_id JOIN product p ON p.id=ci.product_id WHERE u.username='alice' ORDER BY p.id;
SELECT COUNT(*) AS sku_rows,SUM(ci.quantity) AS pieces,SUM(ci.quantity*p.price) AS total_amount FROM cart_item ci JOIN store_user u ON u.id=ci.user_id JOIN product p ON p.id=ci.product_id WHERE u.username='alice';
'@
  $fixture | Set-Content -LiteralPath (Join-Path $out 'fixture.sql') -Encoding utf8NoBOM
  $fixture | & $mysqlExe "--defaults-file=$rootConfig" --skip-password "--database=$dbName" --batch --raw 2>&1 | Set-Content -LiteralPath (Join-Path $out 'fixture-result.tsv') -Encoding utf8
  $state.fixtureExitCode=$LASTEXITCODE
  if($state.fixtureExitCode -ne 0){throw 'SQL cart fixture failed'}
  $env:CSUCAMPUSCRAFT_DB_URL="jdbc:mysql://127.0.0.1:$dbPort/$dbName"
  $env:CSUCAMPUSCRAFT_DB_USER=$dbUser
  $env:CSUCAMPUSCRAFT_DB_PASSWORD=$password
  $provenance=Get-Content -LiteralPath (Join-Path $out 'artifact-provenance.json') -Raw | ConvertFrom-Json
  if($provenance.reuse_allowed -ne $true){throw 'Current JAR/source identity proof not ready or not accepted'}
  foreach($side in @('user','admin')) {
    $jar="csucampuscraft-$side/target/csucampuscraft-$side-0.0.1-SNAPSHOT.jar"
    $port=if($side -eq 'user'){$userPort}else{$adminPort}
    $appProcess=Start-Process -FilePath "$env:JAVA_HOME\bin\java.exe" -ArgumentList @('-jar',$jar,"--server.port=$port") -WorkingDirectory $repo -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $out "app-$side.stdout.log") -RedirectStandardError (Join-Path $out "app-$side.stderr.log")
    if($side -eq 'user'){$state.userPid=$appProcess.Id}else{$state.adminPid=$appProcess.Id}
    Save-Json 'state.json' $state
  }
  $state.phase='MySQL imported, SQL-only cart fixture installed, apps started; login precheck pending'
  Save-Json 'state.json' $state
  @{password=$password;state=$state} | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath (Join-Path $caseTemp 'private-state.json') -Encoding utf8
  $pointer=@{mysql_exe=$mysqlExe;root_defaults_file=$rootConfig;app_defaults_file=$appConfig;database=$dbName;db_port=$dbPort;user_url=$state.userUrl;admin_url=$state.adminUrl;mysql_pid=$state.mysqlStartedPid;user_pid=$state.userPid;admin_pid=$state.adminPid;datadir=$dataDir;server_uuid=$state.serverUuid;private_state_file=(Join-Path $caseTemp 'private-state.json');temp_directory=$caseTemp}
  $pointer | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path ([IO.Path]::GetTempPath()) 'personal-check-connection.json') -Encoding utf8
  Write-Output ('PERSONAL_DB_PORT='+$dbPort)
  Write-Output ('PERSONAL_USER_URL='+$state.userUrl)
  Write-Output ('PERSONAL_ADMIN_URL='+$state.adminUrl)
  Write-Output ('CONNECTION_POINTER='+(Join-Path ([IO.Path]::GetTempPath()) 'personal-check-connection.json'))
} catch {
  $state.phase='Preparation failed; retained raw outputs; no human action recorded'
  $state.error=$_.Exception.Message
  Save-Json 'state.json' $state
  throw
}
