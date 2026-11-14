from pathlib import Path
base=Path(__file__).resolve().parent
old=(base.parent.parent/'step04-auth/verification/verify_step04.py').read_text(encoding='utf-8-sig')
header=old[:old.index('def fixture_update')]
header=header.replace('STEP04','STEP05').replace('STEP04','STEP05').replace("BASELINE='f5372631f24dc265abda7eeeb2711584417abfe9'","BASELINE='a8438b72493fba108577e0ba4918e61b043b8916'").replace("'scope':'STEP05 identity/login/logout/CSRF only; later business and TST-39 remain pending'","'scope':'STEP05 admin category/product/replenishment only; concurrency and faults remain STEP13'")
header=header.replace('urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar),NoRedirect())','urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPCookieProcessor(self.jar),NoRedirect())')
header=header.replace('import os,sys,re,json,time,socket,secrets,hashlib,subprocess,datetime,traceback,urllib.request,urllib.error,urllib.parse,http.cookiejar,zipfile,struct','import os,sys,re,json,time,socket,secrets,hashlib,subprocess,datetime,traceback,urllib.request,urllib.error,urllib.parse,http.cookiejar,zipfile,struct,gzip')
header=header.replace("f'--server.port={port}']","f'--server.port={port}','--server.address=127.0.0.1']")
header=header.replace("if cl.get('/login',port,recorded=False)[0]==200:return p","""if cl.get('/login',port,recorded=False)[0]==200 and 'Started CSUCampusCraft' in log.read_text(encoding='utf-8',errors='replace'):
                owner=command([Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/powershell.exe','-NoLogo','-NoProfile','-Command',f"Get-NetTCPConnection -LocalPort {port} -State Listen | Select-Object -ExpandProperty OwningProcess"],timeout=20)
                pids=[int(x) for x in owner.stdout.decode(errors='replace').split() if x.isdigit()]
                check(app+'-listener-owned-by-created-process',owner.returncode==0 and pids and all(x==p.pid for x in pids))
                record('listener-ownership.jsonl',{'app':app,'port':port,'created_pid':p.pid,'observed_pids':pids,'passed':True})
                return p""")
begin=header.index('def assert_page(');finish=header.index('\ndef login_page(',begin)
header=header[:begin]+'''def assert_page(r,status,name):
    check(name+'-status',r[0]==status,str(status))
    if status in (302,303):return
    check(name+'-html',r[1].get('Content-Type','').startswith('text/html'))
    text=r[2].decode('utf-8')
    check(name+'-no-secrets',PASSWORD not in text and not re.search(r'\\\\$2[aby]\\\\$\\\\d\\\\d\\\\$[./A-Za-z0-9]{53}',text))
    if status>=400:
        feedback=r[3].find(lambda n:n.a.get('role')=='alert' or 'field-error' in n.a.get('class',''))
        check(name+'-error-feedback',feedback is not None or str(status) in r[3].text())
        check(name+'-no-technical-leak','java.lang.' not in text and 'jdbc:mysql:' not in text and 'SELECT ' not in text)

''' +header[finish:]
a=header.index('            http_no+=1;filename=')
b=header.index("        check('no-session-url-rewriting-",a)
header=header[:a]+'''            http_no+=1
            redacted=scrub(text).encode('utf-8');digest=hashlib.sha256(redacted).hexdigest()
            filename='bodies/'+digest[:24]+'.body.gz'
            if not (EV/filename).exists():
                (EV/filename).parent.mkdir(exist_ok=True)
                (EV/filename).write_bytes(gzip.compress(redacted,mtime=0))
            record('http.jsonl',{'sequence':http_no,'method':method,'path':path,'port':port,'status':r.code,'content_type':h.get('Content-Type'),'location':h.get('Location'),'cookie_names':[c.name for c in self.jar],'cookie_values_recorded':False,'set_cookie_present':bool(r.headers.get_all('Set-Cookie',[])),'form_fields':sorted(form.keys()) if isinstance(form,dict) else None,'body_file':filename,'body_encoding':'gzip','redacted_body_sha256':digest,'redacted':True})
''' + header[b:]
header=header.replace("inline400=status==400 and r[3].find(lambda n:n.a.get('data-page-id') in ['U04','A01']) is not None", "inline400=status==400 and r[3].find(lambda n:n.a.get('data-page-id') in ['U04','A01','A03','A05']) is not None")
start=header.index('def snapshot():')
end=header.index('\ndef start_env()',start)
header=header[:start]+r'''def snapshot():
    query="".join("SELECT '__STEP05_"+t+"__';SELECT COUNT(*) FROM "+t+";SELECT * FROM "+t+" ORDER BY id;" for t in TABLES)
    data=sql(query,'csucampuscraft').stdout;out={}
    for i,t in enumerate(TABLES):
        marker=('__STEP05_'+t+'__').encode();start=data.index(marker)+len(marker)
        start+=2 if data[start:start+2]==b'\r\n' else 1
        end=data.index(('__STEP05_'+TABLES[i+1]+'__').encode(),start) if i+1<len(TABLES) else len(data)
        payload=data[start:end];count,raw=payload.split(b'\n',1)
        out[t]={'rows':int(count),'sha256':hashlib.sha256(raw).hexdigest()}
    return out

''' + header[end:]
(base/'verify_step05.py').write_text(header+(base/'cases.pyfrag').read_text(encoding='utf-8'),encoding='utf-8',newline='\n')
print('Generated STEP05 tool using hardened UTC/de-identified runtime helpers')

