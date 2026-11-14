"""New review runner; no product imports, no old test verdicts inherited."""
from pathlib import Path
from html.parser import HTMLParser
from datetime import datetime, timezone
import hashlib, json, subprocess, re, html, time
import requests

ROOT = Path(__file__).resolve().parent
TABLES = ['store_user','category','product','product_image','cart_item','sales_order','sales_order_item']
def stamp(): return datetime.now(timezone.utc).isoformat()
def dump(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
class Elements(HTMLParser):
    def __init__(self, body):
        super().__init__(); self.tags=[]; self.feed(body)
    def handle_starttag(self,tag,attrs): self.tags.append((tag,dict(attrs)))

class Review:
    def __init__(self, cfgpath):
        self.cfg=json.loads(Path(cfgpath).read_text(encoding='utf-8-sig'))
        self.cfgpath=str(cfgpath); self.checks=[]; self.state={}; self.n=0; self.stage='setup'; self.stage_start=0
        self.secrets=set(); self.private=set()
        for q in ["SELECT email,phone FROM store_user", "SELECT receiver_name,receiver_phone,receiver_address FROM sales_order"]:
            for row in self.sql(q, log=False):
                self.private.update(v for v in row.values() if v and v!='NULL')
        self.private.update(['复核收货人','000-REVIEW','测试校区虚构地址'])
    def sql(self, query, log=True):
        cmd=[self.cfg['mysql_exe'],'--defaults-extra-file='+self.cfg['root_defaults_file'],'--default-character-set=utf8mb4','--batch','--raw','--database='+self.cfg['database'],'--execute',"SET time_zone='+00:00'; "+query]
        p=subprocess.run(cmd,capture_output=True,encoding='utf-8',errors='replace')
        if p.returncode: raise RuntimeError('mysql exit '+str(p.returncode)+': '+p.stderr)
        lines=p.stdout.splitlines(); result=[]
        if lines:
            header=lines[0].split('\t'); result=[dict(zip(header,x.split('\t'))) for x in lines[1:]]
        if log:
            with (ROOT/'sql.jsonl').open('a',encoding='utf-8') as f: f.write(json.dumps({'at':stamp(),'stage':self.stage,'sql':query,'exit':p.returncode,'rows':result},ensure_ascii=False)+'\n')
        return result
    def digest(self):
        result={}
        for t in TABLES:
            rows=self.sql('SELECT * FROM '+t+' ORDER BY id',log=False)
            raw=json.dumps(rows,sort_keys=True,ensure_ascii=False).encode()
            result[t]={'rows':len(rows),'sha256':hashlib.sha256(raw).hexdigest()}
        return result
    def check(self,name,ok,detail=None):
        item={'at':stamp(),'stage':self.stage,'name':name,'passed':bool(ok),'detail':detail}
        self.checks.append(item)
        with (ROOT/'checks.jsonl').open('a',encoding='utf-8') as f: f.write(json.dumps(item,ensure_ascii=False)+'\n')
        print(('PASS ' if ok else 'FAIL ')+self.stage+' '+name,flush=True)
    def begin(self,stage): self.stage=stage; self.stage_start=len(self.checks)
    def inputs(self,response):
        return {a['name']:a.get('value','') for t,a in Elements(response.text).tags if t=='input' and 'name' in a}
    def attrs(self,response,name): return [a[name] for t,a in Elements(response.text).tags if name in a]
    def sanitize(self,txt):
        for v in sorted(self.private|self.secrets,key=len,reverse=True):
            if len(v)>=3: txt=txt.replace(v,'[REDACTED]')
        return txt
    def req(self,session,base,method,path,data=None,expected=200,label='',csrf=True,zero=False):
        url=self.cfg['user_url' if base=='u' else 'admin_url']+path
        payload=dict(data or {})
        if method!='GET' and csrf and '_csrf' not in payload:
            # The caller's latest GET, or a read of login, supplies the session token.
            token=getattr(session,'review_csrf',None)
            if token: payload['_csrf']=token
        before=self.digest() if method!='GET' else None
        start=time.monotonic(); response=session.request(method,url,data=payload if method!='GET' else None,allow_redirects=False,timeout=30)
        response.encoding='utf-8'
        parsed=self.inputs(response)
        if parsed.get('_csrf'): session.review_csrf=parsed['_csrf']; self.secrets.add(parsed['_csrf'])
        if parsed.get('confirmationToken'): self.secrets.add(parsed['confirmationToken'])
        for v in payload.values():
            if v and v in [payload.get('_csrf'),payload.get('confirmationToken'),payload.get('password')]: self.secrets.add(str(v))
        after=self.digest() if method!='GET' else None
        self.n+=1; fname=f'http/{self.n:04d}-{self.stage}.html'
        (ROOT/'http').mkdir(exist_ok=True)
        safe=self.sanitize(response.text)
        (ROOT/fname).write_text(safe,encoding='utf-8')
        record={'id':self.n,'at':stamp(),'stage':self.stage,'label':label,'base':base,'method':method,'path':path,'request':{k:('[REDACTED]' if k in ['password','_csrf','confirmationToken','receiverName','receiverPhone','receiverAddress'] else v) for k,v in payload.items()},'status':response.status_code,'location':response.headers.get('Location'),'cookie_names':[c.name for c in session.cookies],'set_cookie_names':list(response.cookies.keys()),'seconds':round(time.monotonic()-start,3),'body':fname,'body_sha256':hashlib.sha256(safe.encode()).hexdigest(),'before':before,'after':after,'changed_tables':[] if before is None else [t for t in TABLES if before[t]!=after[t]]}
        with (ROOT/'http.jsonl').open('a',encoding='utf-8') as f: f.write(json.dumps(record,ensure_ascii=False)+'\n')
        if expected is not None:
            allowed=expected if isinstance(expected,(tuple,list,set)) else [expected]
            self.check(label or method+' '+path,response.status_code in allowed,{'http':self.n,'expected':list(allowed),'actual':response.status_code})
        if zero: self.check((label or path)+' zero seven-table writes',before==after,{'http':self.n,'changed':record['changed_tables']})
        self.check('response does not expose BCrypt hash '+str(self.n),not re.search(r'\$2[aby]\$\d\d\$',response.text))
        response.review_id=self.n
        return response
    def login(self,base,user,password='CSUCampusCraft123!',expected=303,session=None):
        s=session or requests.Session(); s.trust_env=False
        self.req(s,base,'GET','/login',label=base+' login form')
        self.req(s,base,'POST','/login',{'username':user,'password':password},expected=expected,label=base+' login '+user,zero=True)
        return s
    def fresh(self):
        s=requests.Session(); s.trust_env=False; return s
    def finish(self,stage,notes=None):
        rows=self.checks[self.stage_start:]; bad=[x for x in rows if not x['passed']]
        result={'stage':stage,'tested_sha':'0329c9810c4ad2719c4ae95190ff516d1d21a9ed','finished':stamp(),'executor':'Codex (AI)','checks':len(rows),'failed':bad,'result':'PASS' if not bad else 'FAIL','notes':notes or []}
        dump(ROOT/('stage-'+stage+'.json'),result)
        (ROOT/('stage-'+stage+'.md')).write_text('# 阶段 '+stage+'\n\n结果：'+result['result']+'（只限已执行子项，AI执行）。\n\n'+ '\n'.join('- '+str(n) for n in result['notes'])+'\n\n检查 '+str(len(rows))+' 项；失败 '+str(len(bad))+' 项。详情见 checks.jsonl / http.jsonl / sql.jsonl。\n',encoding='utf-8')
        dump(ROOT/'run-state-public.json',self.state)
        return result
