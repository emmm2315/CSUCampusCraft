"""Own and monitor only a test application child; STOP/RESTART files control its lifecycle."""
import datetime, hashlib, json, os, socket, subprocess, sys, time
from pathlib import Path
import requests

instance_path = Path(sys.argv[1]).resolve()
instance = json.loads(instance_path.read_text(encoding='utf-8'))
directory = instance_path.parent/'application'
directory.mkdir(exist_ok=False)
credentials = json.loads(Path(instance['credentials_private']).read_text(encoding='utf-8'))
env = os.environ.copy(); env.update(credentials)
jar = Path('D:/severlt/实验1/CSUCampusCraft/csucampuscraft-user/target/csucampuscraft-user-0.0.1-SNAPSHOT.jar')
java = Path('C:/Program Files/Microsoft/jdk-21.0.7.6-hotspot/bin/java.exe')
port = int(sys.argv[2]) if len(sys.argv)>2 else 18080
events = []
process = None
session = requests.Session(); session.trust_env=False

def event(name, **detail):
    events.append(dict(event=name,time=datetime.datetime.now(datetime.timezone.utc).isoformat(),**detail))
    (directory/'lifecycle.json').write_text(json.dumps(events,indent=2),encoding='utf-8')

def start():
    with socket.socket() as sock:
        if sock.connect_ex(('127.0.0.1',port))==0: raise RuntimeError('Port already occupied')
    log=(directory/('application-'+str(len(events))+'.log')).open('wb')
    child=subprocess.Popen([str(java),'-jar',str(jar),'--server.address=127.0.0.1',f'--server.port={port}'],
          env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
    log.close()
    event('start',pid=child.pid,port=port,jar_sha256=hashlib.sha256(jar.read_bytes()).hexdigest())
    for _ in range(150):
        if child.poll() is not None: raise RuntimeError('Application exited; inspect private application log')
        try:
            response=session.get(f'http://127.0.0.1:{port}/login',timeout=1)
            if response.status_code==200:
                event('ready',pid=child.pid); print('READY '+str(port),flush=True); return child
        except requests.RequestException: pass
        time.sleep(.2)
    child.terminate(); child.wait(timeout=10)
    raise RuntimeError('Application did not become ready')

def stop(child):
    if child is not None and child.poll() is None:
        child.terminate()
        try: child.wait(timeout=15)
        except subprocess.TimeoutExpired: child.kill(); child.wait(timeout=5)
        event('stop',pid=child.pid,return_code=child.returncode)

try:
    process=start()
    while not (directory/'STOP').exists():
        if process.poll() is not None: raise RuntimeError('Application unexpectedly exited')
        if (directory/'RESTART').exists():
            (directory/'RESTART').unlink(); stop(process); process=start(); event('restarted',pid=process.pid)
        time.sleep(.2)
finally:
    stop(process)
