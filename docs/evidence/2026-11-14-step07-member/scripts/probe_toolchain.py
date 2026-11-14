"""Read-only tool version probes. No network, database startup or dependency install."""
from pathlib import Path
import json
import os
import re
import subprocess

HERE = Path(__file__).resolve().parent
CONFIG = json.loads((HERE / 'toolchain.json').read_text(encoding='utf-8'))


def probe(name, argv, timeout=10):
    try:
        p = subprocess.run(
            [str(v) for v in argv], capture_output=True, timeout=timeout,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
        )
        return {'name': name, 'exit_code': p.returncode,
                'output': (p.stdout + p.stderr).decode('utf-8', errors='replace').strip()}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {'name': name, 'exit_code': None, 'error': type(exc).__name__}


def main():
    java_home = Path(os.environ.get('STEP07_JAVA_HOME', CONFIG['java_home']))
    mysql = Path(os.environ.get('STEP07_MYSQL', CONFIG['mysql']))
    mysqld = Path(os.environ.get('STEP07_MYSQLD', CONFIG['mysqld']))
    checks = [
        probe('java', [java_home / 'bin/java.exe', '-version']),
        probe('javac', [java_home / 'bin/javac.exe', '-version']),
        probe('python', [CONFIG['python'], '--version']),
        probe('node', [CONFIG['node'], '--version']),
        probe('mysql', [mysql, '--no-defaults', '--version']),
        probe('mysqld', [mysqld, '--no-defaults', '--version']),
    ]
    mysql_ok = bool(re.search(r'\b8\.4\.', checks[-1].get('output', '')))
    return {'checks': checks, 'mysql_8_4_ready': mysql_ok,
            'missing_baseline_tools': [] if mysql_ok else ['MySQL8.4 server/client'],
            'database_started': False, 'network_used': False}


if __name__ == '__main__':
    print(json.dumps(main(), ensure_ascii=False, indent=2))
