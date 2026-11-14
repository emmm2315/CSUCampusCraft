"""Seed a private Maven Wrapper cache from an existing local ZIP; no download.

No arguments prints the intended operation. --seed writes only beneath this
script's maven-home directory, and refuses to replace any existing cache.
"""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import json
import shutil
import tempfile
import zipfile

HERE = Path(__file__).resolve().parent
CONFIG = json.loads((HERE / 'toolchain.json').read_text(encoding='utf-8'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', action='store_true')
    args = parser.parse_args()
    properties = Path(CONFIG['repo']) / '.mvn/wrapper/maven-wrapper.properties'
    values = dict(line.split('=', 1) for line in properties.read_text(encoding='utf-8').splitlines()
                  if '=' in line and not line.lstrip().startswith('#'))
    url = values['distributionUrl'].strip()
    archive_name = url.rsplit('/', 1)[-1]
    distribution = archive_name.removesuffix('.zip').removesuffix('-bin')
    if distribution != 'apache-maven-3.9.16':
        raise SystemExit('Recheck local ZIP for the current Wrapper distribution.')
    source = Path(CONFIG['cached_wrapper_distribution'])
    destination = HERE / 'maven-home/wrapper/dists' / distribution / hashlib.sha256(url.encode()).hexdigest()
    if not source.is_file():
        raise SystemExit('Existing local Maven ZIP not found; no download was attempted.')
    plan = {'source': str(source), 'target': str(destination), 'download': False,
            'MAVEN_USER_HOME': str(HERE / 'maven-home'), 'seeded': False}
    if args.seed:
        if destination.exists():
            raise SystemExit('Refusing to replace an existing private Wrapper cache.')
        with zipfile.ZipFile(source) as archive:
            for item in archive.infolist():
                parts = PurePosixPath(item.filename).parts
                if not parts or parts[0] != distribution or '..' in parts or '\\' in item.filename:
                    raise SystemExit('Unsafe or unexpected local archive member.')
            with tempfile.TemporaryDirectory(prefix='wrapper-extract-', dir=HERE) as temp:
                archive.extractall(temp)
                unpacked = Path(temp) / distribution
                if not (unpacked / 'bin/mvn.cmd').is_file():
                    raise SystemExit('Local archive does not contain Maven launcher.')
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(unpacked, destination)
        plan['seeded'] = True
    print(json.dumps(plan, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
