"""Read-only current-tree document/source comparison; writes this directory only."""
from pathlib import Path
import datetime
import hashlib
import json
import re
import subprocess
import zipfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def source(rel, terms):
    p = ROOT / rel
    return [{"path": rel, "line": i, "text": s} for i, s in enumerate(p.read_text(encoding="utf-8").splitlines(), 1)
            if any(t in s for t in terms)]

route_doc = ROOT / "docs/系统设计与路由.md"
route_lines = route_doc.read_text(encoding="utf-8").splitlines()
documented = {"user": [], "admin": []}
part = None
for i, line in enumerate(route_lines, 1):
    if line.startswith("## 用户端路由"):
        part = "user"
    elif line.startswith("## 管理端路由"):
        part = "admin"
    elif line.startswith("## "):
        part = None
    if part and line.startswith("| `"):
        for method, path in re.findall(r"`(GET|POST) (/[^`]*)`", line):
            documented[part].append({"method": method, "path": path, "line": i, "p1": "P1" in line})

actual = {"user": [], "admin": []}
excluded = []
for app in actual:
    for path in sorted((ROOT / f"csucampuscraft-{app}/src/main/java").rglob("*Controller.java")):
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(r'@(Get|Post)Mapping\("([^"\n]*)"\)', text):
            row = {"method": match[1].upper(), "path": match[2], "file": path.relative_to(ROOT).as_posix(),
                   "line": text[:match.start()].count("\n")+1}
            if "verification" in path.parts:
                row["path"] = "/__verification" + row["path"]
                row["reason"] = "仅 verification profile 注册的非持久探针，不计默认产品路由"
                excluded.append(row)
            else:
                actual[app].append(row)

route_results = {}
for app in actual:
    a = {(r["method"],r["path"]) for r in actual[app]}
    d = {(r["method"],r["path"]) for r in documented[app] if not r["p1"]}
    route_results[app] = {"source_count": len(a), "documented_p0_count": len(d),
                          "source_only": sorted(a-d), "document_only": sorted(d-a),
                          "p1_excluded": [r for r in documented[app] if r["p1"]]}

word = next((ROOT / "docs").glob("*.docx"))
word_before = sha(word)
with zipfile.ZipFile(word) as z:
    tree = ET.fromstring(z.read("word/document.xml"))
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs = ["".join(x.text or "" for x in p.findall(".//w:t", ns)) for p in tree.findall(".//w:p", ns)]
    word_excerpts = [{"paragraph": i, "text": p} for i, p in enumerate(paragraphs, 1)
                     if any(t in p for t in ["M0 工程初始化已完成", "当前实现仅到", "M0 仅完成初始化", "STEP12 顾客", "本页在 P0"])]

findings = [
    {"id": "DOC-01", "severity": "P2", "result": "文档缺项", "phenomenon": "需求改量表的失败列未明确下架/不可用商品改量返回409；BR-04已有上架校验总则。当前实现先处理有效版本同值数量（无写入成功），真实改量再查商品状态并409。",
     "evidence": source("docs/需求与业务规则.md", ["| 改量 |", "添加和修改时校验"]) + source("csucampuscraft-user/src/main/java/org/csucampuscraft/storefront/cart/CartService.java", ["same-value request", "current.getQuantity() == quantity", "CART_PRODUCT_UNAVAILABLE", "商品已下架或不可用"]),
     "suggestion": "后续文档更新补齐409及同值幂等条件；运行态以本轮B阶段HTTP为准。"},
    {"id": "DOC-02", "severity": "P2", "result": "文案待统一", "phenomenon": "U03游客有货时为登录链接，模板文案“登录后加购”；提示要求返回本页由本人确认。符合先登录再手动加购流程，但规格中的“加入购物车”动作描述未规定链接的确切标签。",
     "evidence": source("csucampuscraft-user/src/main/resources/templates/products/detail.html", ["data-login-to-add", "登录后加购", "请先登录，返回本页"])+source("docs/页面清单与原型.md", ["| U03 |", "| U03 商品详情"]),
     "suggestion": "记录当前真实文案；后续统一交互措辞，不判为功能失败。"},
    {"id": "DOC-03", "severity": "P2", "result": "契约不一致", "phenomenon": "TST-40标准把缺失父版本列为400；当前requireVersion缺失/空白返回409 PRODUCT_IMAGE_VERSION_REQUIRED。",
     "evidence": source("docs/测试与验收用例.md", ["格式缺失 400", "缺失/非法 `productVersion`"])+source("csucampuscraft-admin/src/main/java/org/csucampuscraft/admin/catalog/ProductImageService.java", ["raw == null", "PRODUCT_IMAGE_VERSION_REQUIRED", "缺少商品版本"]),
     "suggestion": "运行态由E阶段重跑确认；后续明确采用400还是409并统一契约。"},
    {"id": "DOC-04", "severity": "P2", "result": "文档过时", "phenomenon": "README当前阶段已写M2闭环，但后文仍把购物车/订单写作后续版本、下一步STEP08；测试文档业务用例导语仍写TST-39继续待实施；路由表用户首页仍称当前主题读取页。",
     "evidence": source("README.md", ["购物车和订单属于后续版本", "下一步为 STEP08", "M2 代码与各步已登记"])+source("docs/测试与验收用例.md", ["TST-39（STEP12）继续待实施"])+source("docs/系统设计与路由.md", ["当前为主题读取页"]),
     "suggestion": "仅登记，STEP13/指导书更新时同步清理当前口径；历史实测段落不改写。"},
    {"id": "DOC-05", "severity": "P2", "result": "待更新", "phenomenon": "Word前言仍为M0已完成、M1尚未开工，当前实现仅主题初始化；与README的M2代码闭环不一致。",
     "evidence": [{"path": word.relative_to(ROOT).as_posix(), **x} for x in word_excerpts],
     "suggestion": "Word待本人完成复核后统一更新，本轮不改。"},
]

steps = []
task_lines = (ROOT / "docs/开发计划与任务.md").read_text(encoding="utf-8").splitlines()
for i,line in enumerate(task_lines,1):
    if re.match(r"\| STEP(?:0[1-9]|1[0-2]) \|",line):
        cells = line.split("|")
        if "负责人" in line:
            steps.append({"line":i,"step":cells[1].strip(),"ledger_status":cells[4].strip()})

report = {
    "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "executor":"Codex AI doc-consistency child agent; not a human signature",
    "baseline_sha": subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
    "method":"current-tree static Controller annotation / documentation comparison and docx ZIP XML extraction; no HTTP results claimed",
    "route_results":route_results,"actual_routes":actual,"documented_routes":documented,
    "excluded_verification_routes":excluded,
    "rest_scope":"系统设计未来REST映射为预留，未并入默认SSR实现差异",
    "word":{"path":word.relative_to(ROOT).as_posix(),"sha256_before":word_before,"sha256_after":sha(word),"unchanged":word_before==sha(word),"paragraph_count":len(paragraphs),"excerpts":word_excerpts},
    "ledger_read_only":steps,"findings":findings,
    "limitations":["Static route declaration comparison does not prove successful runtime dispatch or authorization.","HTTP status and UI wording must use newly run A-E evidence.","No Word editing or rendering; only state text was examined."],
}
(OUT/"audit.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(OUT/"routes.json").write_text(json.dumps(route_results,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
summary = ["# G 文档、路由与 Word 只读核对", "", "执行者：Codex AI；不代表本人或组员完成了人工复核。", "", f"受测源码：`{report['baseline_sha']}`。结论来自本次读取当前树、抽取Controller注解及Word XML，不引用旧证据结论。", "", "## 当前路由静态对照", "", "| 端 | 实际P0 SSR路由 | 文档P0 SSR路由 | 源码独有 | 文档独有 |", "| --- | --- | --- | --- | --- |"]
for app,r in route_results.items():
    summary.append(f"| {app} | {r['source_count']} | {r['documented_p0_count']} | {r['source_only']} | {r['document_only']} |")
summary += ["", "排除 verification profile 的10个非持久探针、P1 receipt、未来REST预留。静态一致不替代HTTP实测。完整方法/路径/源文件行号见 audit.json。", "", "## 问题与待统一事项", ""]
for f in findings:
    summary += [f"### {f['id']} · {f['severity']} · {f['result']}","",f["phenomenon"],"",f["suggestion"],""]
    for e in f["evidence"]:
        loc = f"line {e['line']}" if 'line' in e else f"XML paragraph {e['paragraph']}"
        summary.append(f"- `{e['path']}` {loc}: {e['text']}")
    summary.append("")
summary += ["## 版本与边界", "", f"Word SHA-256：`{word_before}`，本轮只读前后相同。", "台账未修改；STEP02为通过，STEP03–12仍待复核。Word状态登记待更新。", "", "运行命令：`python -X utf8 docs/evidence/2026-11-15-review/doc-audit/audit_docs.py`。", ""]
(OUT/"summary.md").write_text("\n".join(summary),encoding="utf-8")
print(json.dumps({"route_results":route_results,"finding_count":len(findings),"word_unchanged":report['word']['unchanged']},ensure_ascii=False,indent=2))
