"""Offline actual-runner JSON UTF8 regression. No applications, HTTP or DB are started."""
from pathlib import Path
import ast
import hashlib
import json
import subprocess

stage = Path(__file__).resolve().parent.parent
here = stage / 'verification'
out = stage / 'native' / 'concurrent-preflight-utf8-fix'
out.mkdir(parents=True, exist_ok=False)
classes = out / 'classes'
classes.mkdir()
java = Path('C:/Users/Starmetor/.jdks/ms-21.0.12.1/bin/java.exe')
javac = java.parent / 'javac.exe'
classpath = str(classes) + ';' + str(stage / 'native/lib/*')
sources = [here / name for name in ['ConcurrentHttpRunner.java', 'ConcurrentRunnerWirePreflight.java', 'ConcurrentRunnerPrivacyPreflight.java']]
compile_result = subprocess.run([str(javac), '--release', '21', '-encoding', 'UTF-8', '-cp', classpath, '-d', str(classes), *map(str, sources)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
(out / 'compile.log').write_bytes(compile_result.stdout + compile_result.stderr)
assert compile_result.returncode == 0, 'External wire preflight compiler failed'
ast.parse((here / 'concurrency_faults.py').read_text(encoding='utf-8'))
checks = []
for encoding in ['default', 'GBK', 'UTF-8']:
    for mechanism in ['old-print-control', 'actual-writeJson']:
        options = [] if encoding == 'default' else ['-Dstdout.encoding=' + encoding]
        args = [str(java), *options, '-cp', classpath, 'ConcurrentRunnerWirePreflight']
        if mechanism == 'old-print-control':
            args.append('old-print-control')
        result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stem = encoding.replace('-', '') + '-' + mechanism
        (out / (stem + '.stdout.bin')).write_bytes(result.stdout)
        (out / (stem + '.stderr.bin')).write_bytes(result.stderr)
        text = None
        try:
            decoded = result.stdout.decode('utf-8')
            value = json.loads(decoded)
            valid = True
            text = value.get('text')
            observed_charset = value.get('stdout_charset')
        except (UnicodeDecodeError, json.JSONDecodeError):
            valid = False
            observed_charset = None
        exact = text == '\u6821\u56ed\u6bd5\u4e1a\u793c\u76d2\U0001f600'
        checks.append(dict(encoding_option=encoding, mechanism=mechanism, exit_code=result.returncode,
                           strict_utf8_json=valid, exact_chinese_emoji_roundtrip=exact,
                           stdout_bytes=len(result.stdout), stdout_sha256=hashlib.sha256(result.stdout).hexdigest(),
                           observed_stdout_charset=observed_charset))
        assert result.returncode == 0, 'Offline wire helper exited'
        if mechanism == 'actual-writeJson':
            assert valid and exact, 'Actual runner byte method must roundtrip all stdout encodings'
        if encoding == 'GBK' and mechanism == 'old-print-control':
            assert not (valid and exact), 'GBK old-print control must expose old protocol incompatibility'
privacy = subprocess.run([str(java), '-cp', classpath, 'ConcurrentRunnerPrivacyPreflight'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
(out / 'privacy-preflight.log').write_bytes(privacy.stdout + privacy.stderr)
assert privacy.returncode == 0
privacy_result = json.loads(privacy.stdout.decode('utf-8'))
assert privacy_result['overall'] == 'PASS' and privacy_result['checks'] == 12
manifest = dict(overall='PASS', scope='Offline actual new runner writeJson under default/GBK/UTF8 stdout; synthetic old-print negative control; no HTTP/JDBC/application action',
                product_source_sha='d577179e4468354552d3f5f48d624a4296ee3cfb', compiler_exit=compile_result.returncode,
                python_AST_passed=True, wire_cases=checks, actual_runner_privacy_checks=12,
                files=[dict(path=str(p.relative_to(stage)), sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in [*sources, here / 'concurrency_faults.py']])
(out / 'result.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(dict(overall=manifest['overall'], wire_cases=len(checks), privacy_checks=12, output=str(out))))
