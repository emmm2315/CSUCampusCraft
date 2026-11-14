"""Workspace-only MySQL lifecycle. Never opens system default ports or datadirs."""
from pathlib import Path
import argparse
import datetime
import json
import os
import re
import secrets
import socket
import subprocess
import time

HERE = Path(__file__).resolve().parent
REPO = Path(json.loads((HERE / 'toolchain.json').read_text(encoding='utf-8'))['repo'])
FLAG = getattr(subprocess, 'CREATE_NO_WINDOW', 0)


def run(argv, **kwargs):
    return subprocess.run([str(v) for v in argv], capture_output=True, creationflags=FLAG, **kwargs)


def environment(directory):
    env = os.environ.copy()
    for key in ['MYSQL_PWD', 'MYSQL_HOME', 'MYSQL_HOST', 'MYSQL_TCP_PORT', 'MYSQL_UNIX_PORT']:
        env.pop(key, None)
    env['MYSQL_TEST_LOGIN_FILE'] = str(directory / 'unused-login-path.cnf')
    return env


def sql(base, port, directory, query, database=None):
    argv = [base / 'bin/mysql.exe', '--no-defaults', '--protocol=TCP',
            '--host=127.0.0.1', f'--port={port}', '--user=root', '--connect-timeout=2',
            '--default-character-set=utf8mb4', '--batch', '--raw', '--skip-column-names']
    if database:
        argv += [f'--database={database}']
    return run(argv, input=("SET SESSION time_zone='+00:00';" + query).encode('utf-8'),
               env=environment(directory), timeout=30)


def identity(base, port, directory):
    result = sql(base, port, directory, 'SELECT @@version,@@server_uuid,@@port,@@datadir;')
    if result.returncode:
        return None
    values = result.stdout.decode('utf-8').strip().split('\t')
    return {'version': values[0], 'uuid': values[1], 'port': int(values[2]),
            'datadir': str(Path(values[3]).resolve())}


def start(base, label, allow_80):
    base = base.resolve()
    version = run([base / 'bin/mysqld.exe', '--no-defaults', '--version'], timeout=10)
    version_text = (version.stdout + version.stderr).decode(errors='replace')
    baseline = bool(re.search(r'\b8\.4\.', version_text))
    if version.returncode or (not baseline and not (allow_80 and '8.0.44' in version_text)):
        raise SystemExit('MySQL8.4 required; --allow-80 permits only the explicitly labelled8.0.44 compatibility run.')
    directory = (HERE / 'runtime' / label).resolve()
    if not directory.is_relative_to(HERE / 'runtime') or not re.fullmatch(r'[A-Za-z0-9_-]+', label):
        raise SystemExit('Invalid workspace-local attempt label.')
    directory.mkdir(parents=True, exist_ok=False)
    data = directory / 'mysql-data'
    data.mkdir()
    init = run([base / 'bin/mysqld.exe', '--no-defaults', '--initialize-insecure',
                f'--basedir={base}', f'--datadir={data}', f'--log-error={directory / "initialize.log"}'],
               env=environment(directory), timeout=90)
    (directory / 'initialize-console.log').write_bytes(init.stdout + init.stderr)
    if init.returncode:
        raise SystemExit('Initialization failed; inspect the private attempt logs.')
    with socket.socket() as available:
        available.bind(('127.0.0.1', 0))
        port = available.getsockname()[1]
    with (directory / 'server.log').open('wb') as log:
        process = subprocess.Popen([str(base / 'bin/mysqld.exe'), '--no-defaults',
            f'--basedir={base}', f'--datadir={data}', f'--port={port}', '--bind-address=127.0.0.1',
            '--mysqlx=OFF', f'--pid-file={directory / "mysql.pid"}', '--console'],
            env=environment(directory), stdout=log, stderr=subprocess.STDOUT, creationflags=FLAG)
    try:
        deadline = time.monotonic() + 50
        actual = None
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError('New isolated server exited during startup.')
            actual = identity(base, port, directory)
            if actual:
                break
            time.sleep(.2)
        uuid = re.search(r'^server-uuid=(.+)$', (data / 'auto.cnf').read_text(), re.MULTILINE).group(1).strip()
        if not actual or actual['port'] != port or Path(actual['datadir']) != data.resolve() or actual['uuid'] != uuid:
            raise RuntimeError('Isolated server identity check failed before schema writes.')
        schema = 'csucampuscraft'
        created = sql(base, port, directory,
                      f'CREATE DATABASE {schema} CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_as_ci;')
        if created.returncode:
            raise RuntimeError('Creating isolated schema failed.')
        imported = sql(base, port, directory,
                       (REPO / 'database/02-schema-with-demo.sql').read_text(encoding='utf-8-sig'), schema)
        if imported.returncode:
            (directory / 'import-errors.log').write_bytes(imported.stderr)
            raise RuntimeError('Importing isolated demo schema failed.')
        app_password = secrets.token_urlsafe(32)
        grants = sql(base, port, directory,
                     "CREATE USER 'step07_app'@'127.0.0.1' IDENTIFIED BY '" + app_password + "';"
                     "GRANT SELECT,LOCK TABLES ON csucampuscraft.* TO 'step07_app'@'127.0.0.1';"
                     "GRANT INSERT,UPDATE,DELETE ON csucampuscraft.cart_item TO 'step07_app'@'127.0.0.1';")
        if grants.returncode:
            raise RuntimeError('Creating isolated application account failed.')
        credentials = directory / 'credentials-private.json'
        credentials.write_text(json.dumps({'CSUCAMPUSCRAFT_DB_URL': f'jdbc:mysql://127.0.0.1:{port}/{schema}',
                                          'CSUCAMPUSCRAFT_DB_USER': 'step07_app',
                                          'CSUCAMPUSCRAFT_DB_PASSWORD': app_password}), encoding='utf-8')
        manifest = dict(actual, basedir=str(base), mysql=str(base / 'bin/mysql.exe'),
                        mysqld=str(base / 'bin/mysqld.exe'), pid=process.pid, schema=schema,
                        mysql8_4_baseline=baseline, compatibility_only=not baseline,
                        private_directory=str(directory), credentials_private=str(credentials),
                        root_connection='127.0.0.1 only; no password in this temporary initialize-insecure instance',
                        initialized_from='database/02-schema-with-demo.sql',
                        started_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
        (directory / 'instance.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
    except BaseException:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        raise


def inspect_or_stop(manifest_path, stopping):
    manifest_path = manifest_path.resolve()
    if not manifest_path.is_relative_to(HERE / 'runtime'):
        raise SystemExit('Refusing non-workspace instance manifest.')
    saved = json.loads(manifest_path.read_text(encoding='utf-8'))
    base, directory = Path(saved['basedir']), manifest_path.parent
    actual = identity(base, saved['port'], directory)
    if not actual:
        print(json.dumps({'running': False, 'stopped': stopping}))
        return
    matches = all(actual[k] == saved[k] for k in ['uuid', 'port', 'datadir'])
    if not matches:
        raise SystemExit('Target identity differs from this private instance; no action taken.')
    if stopping:
        shutdown = sql(base, saved['port'], directory, 'SHUTDOWN;')
        if shutdown.returncode:
            raise SystemExit('Graceful shutdown request failed; no unidentified process was killed.')
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline and identity(base, saved['port'], directory):
            time.sleep(.2)
        stopped = identity(base, saved['port'], directory) is None
        if stopped:
            Path(saved['credentials_private']).unlink(missing_ok=True)
        print(json.dumps({'stopped': stopped, 'port': saved['port'], 'uuid_verified': True}))
    else:
        print(json.dumps(dict(actual, running=True, uuid_verified=True)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['start', 'status', 'stop'])
    parser.add_argument('--base', type=Path)
    parser.add_argument('--label')
    parser.add_argument('--allow-80', action='store_true')
    parser.add_argument('--manifest', type=Path)
    options = parser.parse_args()
    if options.action == 'start':
        if not options.base or not options.label:
            parser.error('--base and --label required for start')
        start(options.base, options.label, options.allow_80)
    else:
        if not options.manifest:
            parser.error('--manifest required for status/stop')
        inspect_or_stop(options.manifest, options.action == 'stop')
