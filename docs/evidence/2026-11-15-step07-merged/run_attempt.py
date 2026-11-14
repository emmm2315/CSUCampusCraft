from pathlib import Path
import os,subprocess,sys,json
here=Path(__file__).resolve().parent
name=sys.argv[1]
assert name.startswith('attempt') and name[7:].isdigit()
env=os.environ.copy()
env.update(STEP07_TESTED_CODE_SHA='9e61c3e88761519fc63a4d99cafb006a51eacfa5',STEP07_BUILD_LOG_DIR=str(here.parent),PYTHONIOENCODING='utf-8',PYTHONUNBUFFERED='1')
with (here/(name+'-run.log')).open('xb') as log:
    p=subprocess.run([sys.executable,here/'verify_step07.py',name],env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
print(json.dumps({'attempt':name,'exit_code':p.returncode,'raw_log':str(here/(name+'-run.log'))}))
raise SystemExit(p.returncode)
