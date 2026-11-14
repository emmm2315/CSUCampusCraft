$ErrorActionPreference = 'Stop'
$repo='D:\Github Projects\CSUCampusCraft'
Set-Location -LiteralPath $repo
$out=Join-Path $repo 'docs\evidence\2026-11-15-review\environment'
$s=Get-Content (Join-Path $out 'state.json') -Raw | ConvertFrom-Json
$private=Get-Content (Join-Path $s.tempDirectory 'private-state.json') -Raw | ConvertFrom-Json
$env:CSUCAMPUSCRAFT_DB_URL=$s.dbUrl
$env:CSUCAMPUSCRAFT_DB_USER=$s.dbUser
$env:CSUCAMPUSCRAFT_DB_PASSWORD=$private.password
$java='C:\Users\Starmetor\.jdks\ms-21.0.12.1\bin\java.exe'
$jar='csucampuscraft-user/target/csucampuscraft-user-0.0.1-SNAPSHOT.jar'
$args=@('-jar',$jar,'--server.port=18080','--csucampuscraft.checkout.confirmation-ttl=PT2S')
Add-Content -LiteralPath (Join-Path (Split-Path $out) 'commands-environment.md') -Encoding utf8 -Value ('`Start-Process -FilePath '+$java+' -ArgumentList '+($args -join ' ')+' -WindowStyle Hidden -PassThru`')
$p=Start-Process -FilePath $java -ArgumentList $args -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $out 'app-short-ttl.stdout.log') -RedirectStandardError (Join-Path $out 'app-short-ttl.stderr.log')
@{pid=$p.Id;port=18080;url='http://127.0.0.1:18080';ttl='PT2S';jar=$jar;defaultUserUnchanged=$true;createdAt=(Get-Date -Format o)} | ConvertTo-Json | Set-Content (Join-Path $out 'short-ttl-state.json') -Encoding utf8
$conn=Get-Content (Join-Path ([IO.Path]::GetTempPath()) 'review-connection.json') -Raw | ConvertFrom-Json
$conn | Add-Member -NotePropertyName short_user_url -NotePropertyValue 'http://127.0.0.1:18080' -Force
$conn | Add-Member -NotePropertyName short_user_pid -NotePropertyValue $p.Id -Force
$conn | ConvertTo-Json -Depth 5 | Set-Content (Join-Path ([IO.Path]::GetTempPath()) 'review-connection.json') -Encoding utf8
Write-Output ('SHORT_TTL_PID='+$p.Id)
