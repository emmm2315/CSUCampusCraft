# 环境阶段真实命令

本文件由 prepare.ps1 在执行时追加。密码在临时 defaults 文件中，未归档。

`Get-Process java,mysqld -ErrorAction SilentlyContinue; netstat -ano -p tcp`
`& $env:JAVA_HOME\bin\java.exe -version`
`.\mvnw.cmd -v`
`.\mvnw.cmd -f csucampuscraft-user/pom.xml clean verify`
`.\mvnw.cmd -f csucampuscraft-admin/pom.xml clean verify`
`& D:\MySQL\bin\mysqld.exe --version; & D:\MySQL\bin\mysql.exe --version`
`D:\MySQL\bin\mysqld.exe --no-defaults --initialize-insecure --basedir=D:\MySQL --datadir=C:\Users\Starmetor\AppData\Local\Packages\openai.codex_2p2nqsd0c76g0\AC\#!sandbox.{1c73837d-3f78-465d-bb61-08606559fbd7}\Temp\csucampuscraft-review-20261115-9ab54c7ca6bf43dda7275d09685a047c\data --console`
`D:\MySQL\bin\mysqld.exe --no-defaults --initialize-insecure --basedir=D:\MySQL --datadir=C:\Users\Starmetor\AppData\Local\Temp\csucampuscraft-review-20261115-b53811e5a70e42d792037669ec7cad67\data --console`
`Start-Process -FilePath D:\MySQL\bin\mysqld.exe -ArgumentList --no-defaults --basedir=D:\MySQL --datadir=C:\Users\Starmetor\AppData\Local\Temp\csucampuscraft-review-20261115-b53811e5a70e42d792037669ec7cad67\data --bind-address=127.0.0.1 --port=59315 --mysqlx=0 --default-time-zone=+00:00 --console -WindowStyle Hidden -PassThru (stdout/stderr archived)`
`mysql --defaults-file=<temporary root.cnf> --skip-password (stdin CREATE DATABASE csucampuscraft/review_schema; CREATE USER review_app; GRANT SELECT,INSERT,UPDATE,DELETE; random password omitted)`
`mysql --defaults-file=<temporary root.cnf> --skip-password --database=csucampuscraft --execute="SOURCE database/02-schema-with-demo.sql"`
`mysql --defaults-file=<temporary root.cnf> --skip-password --database=review_schema --execute="SOURCE database/01-schema.sql"`
`mysql --defaults-file=<temporary root.cnf> --skip-password --database=csucampuscraft --batch --execute=<counts.sql>`
`mysql --defaults-file=<temporary root.cnf> --skip-password --database=review_schema --batch --execute=<counts.sql>`
`Start-Process -FilePath C:\Users\Starmetor\.jdks\ms-21.0.12.1\bin\java.exe -ArgumentList '-jar',csucampuscraft-user/target/csucampuscraft-user-0.0.1-SNAPSHOT.jar -WindowStyle Hidden -PassThru (CSUCAMPUSCRAFT_DB_URL/USER/PASSWORD inherited)`
`Start-Process -FilePath C:\Users\Starmetor\.jdks\ms-21.0.12.1\bin\java.exe -ArgumentList '-jar',csucampuscraft-admin/target/csucampuscraft-admin-0.0.1-SNAPSHOT.jar -WindowStyle Hidden -PassThru (CSUCAMPUSCRAFT_DB_URL/USER/PASSWORD inherited)`

`D:/MySQL/bin/mysql.exe --defaults-file=C:\Users\Starmetor\AppData\Local\Temp\csucampuscraft-review-20261115-b53811e5a70e42d792037669ec7cad67\root.cnf --skip-password --database=csucampuscraft --batch --raw < environment/server.sql`

`D:/MySQL/bin/mysql.exe --defaults-file=C:\Users\Starmetor\AppData\Local\Temp\csucampuscraft-review-20261115-b53811e5a70e42d792037669ec7cad67\root.cnf --skip-password --database=csucampuscraft --batch --raw < environment/checks.sql`

`D:/MySQL/bin/mysql.exe --defaults-file=C:\Users\Starmetor\AppData\Local\Temp\csucampuscraft-review-20261115-b53811e5a70e42d792037669ec7cad67\root.cnf --skip-password --database=csucampuscraft --batch --raw < environment/sessions.sql`

`D:/MySQL/bin/mysql.exe --defaults-file=C:\Users\Starmetor\AppData\Local\Temp\csucampuscraft-review-20261115-b53811e5a70e42d792037669ec7cad67\root.cnf --skip-password --database=csucampuscraft --batch --raw < environment/indexes.sql`
`Start-Process -FilePath C:\Users\Starmetor\.jdks\ms-21.0.12.1\bin\java.exe -ArgumentList -jar csucampuscraft-user/target/csucampuscraft-user-0.0.1-SNAPSHOT.jar --server.port=18080 --csucampuscraft.checkout.confirmation-ttl=PT2S -WindowStyle Hidden -PassThru`
`pwsh -NoProfile -File environment/capture_ownership.ps1 (CIM, Get-NetTCPConnection, MySQL processlist+time_zone join)`
`pwsh -NoProfile -File environment/stop-short-ttl.ps1 (verify PID2276 command and 18080 listener; Stop-Process -Id 2276)`
`pwsh -NoProfile -File environment/import-reference.ps1 (verify @@port/@@datadir, CREATE DATABASE review_reference, mysql --database=review_reference --execute="SOURCE database/02-schema-with-demo.sql", seven-table counts)`
`pwsh -NoProfile -File environment/restart-main.ps1 (verify old PIDs/JAR SHA/listeners, Stop-Process old main PIDs, Start-Process same JAR/environment -WindowStyle Hidden, confirm new listeners, update temporary connection PIDs; no DB writes)`
`pwsh -NoProfile -File environment/final-stop.ps1 (SELECT @@port/@@datadir/@@server_uuid; verify PID/command/listener; Stop-Process 37480/3936; mysqladmin --defaults-file=<temporary root.cnf> --skip-password shutdown; read native exit codes and remaining processes/listeners; retain temporary files)`
