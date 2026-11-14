# G 阶段复现命令与工具运行记录

工作目录：`D:\Github Projects\CSUCampusCraft`。只读旧证据与 Git 对象；所有新输出在本次 review 目录内。

```powershell
python -X utf8 docs/evidence/2026-11-15-review/integrity/verify_integrity.py
python -X utf8 docs/evidence/2026-11-15-review/integrity/newline_diagnostic.py
python -X utf8 -c "import subprocess,json,datetime;from pathlib import Path;p=subprocess.run(['python','-X','utf8','docs/evidence/2026-11-15-review/integrity/verify_integrity.py'],capture_output=True);o={'argv':['python','-X','utf8','docs/evidence/2026-11-15-review/integrity/verify_integrity.py'],'exit_code':p.returncode,'stdout':p.stdout.decode('utf-8',errors='replace'),'stderr':p.stderr.decode('utf-8',errors='replace'),'finished_at':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()};Path('docs/evidence/2026-11-15-review/integrity/run-result.json').write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(o['stdout']);print(o['stderr']);print('exit',p.returncode)"
```

上面是实际运行顺序：首次主脚本退出 0；发现少量原清单与 LF/CRLF 两种形态均不同，随后独立诊断精确重建混合换行，最后主脚本加入该诊断的逐项复验再退出 0。首次运行出现 Python 3.14 的正则字符串 `\d` SyntaxWarning，已改为 raw string；警告不影响首次退出码。两次均有本机 Python 启动器 `Failed to find real location ... python.exe` 提示，但 Python 脚本正常执行，最终真实 stdout/stderr/exit 见 `run-result.json`。

主脚本的真实 Git argv、退出码和结果在 `commands.json`；`git cat-file --batch` 的输入对象列表也保存，避免依赖临时工作树。所有归档文件的 text 属性真实批量命令与结果在 `text-attributes.json`。`newline_diagnostic.py` 的 Git show 参数固定在脚本中，输出 `newline-diagnostic.json`。无需检出旧分支，也不写原源码。

另外保留一次调查工具错误：下列实际临时命令在读取 Git 之前就因 Python comprehension 变量作用域退出 1，随后改用独立可读脚本 `newline_diagnostic.py`。这是本轮工具错误，不是产品错误。

```powershell
python -X utf8 -c "import subprocess,hashlib,difflib,json;from pathlib import Path;cases=[('1aa6ad0c4a7546c5bfba7ed65ef05f5913132027','93f3c461163ff09f54b667299360068d450ca254','2026-11-14-step06'),('39c96aaaad18c58dce9d57450e14317a75c29b3d','8dd7794e5b84fbc9a95069b76a74b761218e6d0a','2026-11-14-step11'),('03384367c87147f1c29859c799f3c464b016b760','a899cce263526926292afec8ed55d6757aed0597','2026-11-15-step12')];[(print(n,e['path'],[(a,c,hashlib.sha256(b''.join([(x.rstrip(b'\r\n')+(b'\r\n' if (i in same)==a else b'\n')) for i,x in enumerate(new)])).hexdigest()==e['expected_sha256']) for a in [False,True] for c,new,old,same in [(None,new,old,{j for block in difflib.SequenceMatcher(None,old,new,autojunk=False).get_matching_blocks() for j in range(block.b,block.b+block.size)})]])) for s,base,n in cases for m in json.loads((Path('docs/evidence/2026-11-15-review/integrity')/(n+'.json')).read_text(encoding='utf-8'))['runtime_manifests'][-1:] for e in m['entries'] if not(e['tested_git_blob_exact_match'] or e['tested_git_blob_crlf_reconstruction_match']) for new,old in [(subprocess.check_output(['git','show',s+':'+e['path']]).splitlines(keepends=True),subprocess.check_output(['git','show',base+':'+e['path']]).splitlines(keepends=True))]]"
```

实际错误：`UnboundLocalError: cannot access local variable 'new' where it is not associated with a value`，退出 1。只影响该临时诊断输出；没有写任何旧文件、源码或数据库。
