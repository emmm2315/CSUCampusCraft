from pathlib import Path
from html.parser import HTMLParser
from collections import Counter
import hashlib, json, subprocess, sys

ROOT=Path('D:/Github Projects/CSUCampusCraft')
STAGE=Path(__file__).resolve().parent.parent
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def git(*a):return subprocess.check_output(['git',*a],cwd=ROOT).decode('utf-8').strip()
class Contract(HTMLParser):
    def __init__(self):super().__init__(convert_charrefs=True);self.items=[];self.text=[]
    def handle_starttag(self,tag,attrs):
        frozen={k:v for k,v in attrs if k.startswith('data-') or k in ('id','name','method','action') or (k.startswith('th:') and k not in ('th:class','th:classappend'))}
        if frozen:self.items.append({'tag':tag,'attrs':frozen})
    handle_startendtag=handle_starttag
    def handle_data(self,value):
        value=' '.join(value.split())
        if value:self.text.append(value)
def extract(p):
    c=Contract();c.feed(p.read_text(encoding='utf-8-sig'));return {'elements':c.items,'text':c.text}
def counter(items):return Counter(json.dumps(x,ensure_ascii=False,sort_keys=True) for x in items)
mode=sys.argv[1]
if mode=='before':
    assert git('rev-parse','HEAD')=='e2bdeb9df9cc7888383ef7afa28d5fbe94f29696'
    assert git('branch','--show-current')=='feat/ui-redesign'
    assert not git('status','--porcelain')
    target=STAGE/'baseline';target.mkdir(exist_ok=True)
    assert not (target/'tracked-sha256.json').exists()
    files=[p for p in subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0') if p]
    hashes={p:digest(ROOT/p) for p in files}
    (target/'tracked-sha256.json').write_text(json.dumps(hashes,ensure_ascii=False,indent=2),encoding='utf-8')
    templates={p:extract(ROOT/p) for p in files if '/src/main/resources/templates/' in p and p.endswith('.html')}
    (target/'selectors-before.json').write_text(json.dumps(templates,ensure_ascii=False,indent=2),encoding='utf-8')
    for p in templates:
        dest=target/'templates'/p;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((ROOT/p).read_bytes())
    (target/'identity.json').write_text(json.dumps({'sha':git('rev-parse','HEAD'),'branch':git('branch','--show-current'),'main':git('rev-parse','main'),'tracked':len(files),'templates':len(templates)},indent=2),encoding='utf-8')
    print(json.dumps({'tracked_files':len(hashes),'templates':len(templates),'contract_elements':sum(len(x['elements']) for x in templates.values())}))
elif mode in ('after','candidate'):
    target=STAGE/'baseline';before=json.loads((target/'selectors-before.json').read_text(encoding='utf-8'))
    after={p:extract((STAGE/'candidate'/p) if mode=='candidate' and (STAGE/'candidate'/p).is_file() else ROOT/p) for p in before}
    results=[]
    for p,old in before.items():
        new=after[p];missing=counter(old['elements'])-counter(new['elements']);added=counter(new['elements'])-counter(old['elements'])
        # Added visual html attributes must not make an original element look removed.
        old_items=old['elements'];new_items=new['elements'];unmatched=list(new_items);lost=[]
        for item in old_items:
            match=next((i for i,v in enumerate(unmatched) if v['tag']==item['tag'] and all(v['attrs'].get(k)==value for k,value in item['attrs'].items())),None)
            if match is None:lost.append(item)
            else:unmatched.pop(match)
        text_missing=Counter(old['text'])-Counter(new['text'])
        results.append({'file':p,'original_contract_elements':len(old_items),'missing_or_changed':lost,'new_or_extended_elements':[json.loads(k) for k,v in added.items() for _ in range(v)],'original_text_missing':dict(text_missing)})
    report={'baseline_sha':json.loads((target/'identity.json').read_text())['sha'],'templates':len(before),'missing_or_changed_count':sum(len(x['missing_or_changed']) for x in results),'original_text_missing_count':sum(sum(x['original_text_missing'].values()) for x in results),'files':results,'policy':'Preserve each original tag and all data/id/name/action/method/Thymeleaf bindings; additions limited to presentation or accessibility. New html data-ef-variant/data-theme are visual-only.'}
    out=STAGE/('candidate-preservation.json' if mode=='candidate' else 'selector-preservation.json');out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    (STAGE/('selectors-candidate.json' if mode=='candidate' else 'selectors-after.json')).write_text(json.dumps(after,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='files'},ensure_ascii=False))
    assert report['missing_or_changed_count']==0
    assert report['original_text_missing_count']==0
