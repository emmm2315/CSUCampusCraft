import json,pathlib,re,datetime
p=pathlib.Path(__file__).resolve().parent
s=json.loads((p/'state.json').read_text(encoding='utf-8-sig'))
secret=json.loads((pathlib.Path(s['tempDirectory'])/'private-state.json').read_text(encoding='utf-8-sig'))['password'].encode()
files=[x for x in p.rglob('*') if x.is_file() and '__pycache__' not in x.parts]
files.extend([p.parent/'environment.md',p.parent/'stage-0.md',p.parent/'commands-environment.md'])
findings=[]
for path in files:
    raw=path.read_bytes()
    checks={'temporary_app_password':secret in raw,
      'literal_session_cookie':bool(re.search(rb'CSUCAMPUSCRAFT_(?:USER|ADMIN)_SESSION=[A-Za-z0-9+/_-]{12,}',raw)),
      'literal_csrf_input':bool(re.search(rb'name=["\x27]_csrf["\x27][^>\r\n]*value=["\x27][A-Za-z0-9+/_=-]{16,}["\x27]',raw)),
      'literal_confirmation_input':bool(re.search(rb'name=["\x27]confirmationToken["\x27][^>\r\n]*value=["\x27][A-Za-z0-9+/_=-]{16,}["\x27]',raw))}
    if any(checks.values()):findings.append({'path':str(path.relative_to(p.parent)),'categories':[k for k,v in checks.items() if v]})
result={'checkedAt':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),'scope':'environment/ files + environment.md + stage-0.md + commands-environment.md','filesScanned':len(files),'temporaryAppPasswordExactMatchCount':sum('temporary_app_password' in x['categories'] for x in findings),'sessionCsrfConfirmationPatternFindings':findings,'containsRawSecretValuesInThisReport':False,'publicTeachingPasswordIsExpectedInReproductionSource':True,'result':'PASS' if not findings else 'FAIL'}
(p/'sensitive-scan-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k in ['filesScanned','temporaryAppPasswordExactMatchCount','result']},ensure_ascii=False))
