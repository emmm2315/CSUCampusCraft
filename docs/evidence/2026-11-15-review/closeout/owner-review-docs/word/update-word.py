"""Targeted OOXML text-only closeout. Run with the bundled workspace Python."""
import hashlib
import json
from pathlib import Path
import re
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape
from zipfile import ZipFile
from docx import Document

ROOT = Path('D:/Github Projects/CSUCampusCraft')
SOURCE = ROOT / 'docs/实验一 CSUCampusCraft 校园文创商店实验指导书.docx'
OUT = ROOT / 'docs/evidence/2026-11-15-review/closeout/owner-review-docs/word'
QA = OUT / '_qa'
QA.mkdir(parents=True, exist_ok=True)
baseline = SOURCE.read_bytes()
assert hashlib.sha256(baseline).hexdigest() == '1202242524c1e3947de820761b9a976376d8410615b43118202f1de69ff21f93', 'Run only against the recorded pre-closeout Word baseline.'
(QA / 'before.docx').write_bytes(baseline)
old_doc = Document(SOURCE)
paragraphs = [p.text for p in old_doc.paragraphs]

replacements = {
    3: '当前状态：STEP01–12 已交付；M0/M1/M2 完成；M2 已完成 2026-11-15 本人复核（高宇弘；组员互评未实施，AI 辅助实测）；STEP13 整体验收待执行；P1 未选做。M0 曾在独立目录和隔离 MySQL 自动复现双端构建、启动、同库读取、重启保留与共享图片，记录见《测试与验收用例》。以下步骤的操作指引保留；STEP01–12 已按本指导书实现并通过本人复核，STEP13 按本指导书执行整体验收。',
    19: paragraphs[19].replace('；两人组可以分担 C。', '；两人组可以分担 C。实际执行说明：本项目由本人高宇弘执行（AI 辅助），复核由本人于 2026-11-15 完成；课程模板分工未按三人组实施，组员互评未实施。'),
    37: paragraphs[37].replace('M0 尚无登录页面，账号用于 STEP04 及以后。', 'M0 阶段尚无登录页面（历史状态）；当前 STEP04 登录已交付并通过本人复核，账号用于 STEP04 及以后。'),
    51: paragraphs[51].replace('当前实现仅到主题读取与初始化，规划页面待开发。', '“仅到主题读取与初始化”为 M0 历史状态；当前 STEP01–12 已交付并通过本人复核，STEP13 整体验收待执行。'),
    292: paragraphs[292].replace('M0 仅完成初始化，尚不具备完整交易页面；不能把以下步骤写成已演示。', 'STEP01–12 已交付并通过 2026-11-15 本人复核；以下操作指引保留，未实际执行的完整演示与 STEP13 整体验收仍须另行记录。'),
}
with ZipFile(SOURCE) as archive:
    entries = [(info, archive.read(info.filename)) for info in archive.infolist()]
xml = dict((i.filename, b) for i, b in entries)['word/document.xml'].decode('utf-8')
old_xml = xml
changes = []
for index, updated in replacements.items():
    original = paragraphs[index]
    assert len(old_doc.paragraphs[index].runs) == 1
    assert updated != original
    assert xml.count(escape(original)) == 1, (index, 'source text must occur exactly once')
    xml = xml.replace(escape(original), escape(updated), 1)
    changes.append({'paragraph_index_zero_based': index, 'before': original, 'after': updated})
ET.fromstring(xml)
new_path = QA / 'updated.docx'
with ZipFile(new_path, 'w') as archive:
    for info, data in entries:
        archive.writestr(info, xml.encode('utf-8') if info.filename == 'word/document.xml' else data)
new_doc = Document(new_path)
new_paragraphs = [p.text for p in new_doc.paragraphs]
assert len(new_paragraphs) == len(paragraphs)
assert all(new_paragraphs[i] == replacements.get(i, text) for i, text in enumerate(paragraphs))
assert len(new_doc.tables) == len(old_doc.tables)
assert [t._tbl.xml for t in new_doc.tables] == [t._tbl.xml for t in old_doc.tables]
assert re.sub(r'<w:t(?: [^>]*)?>.*?</w:t>', '<w:t/>', old_xml, flags=re.S) == re.sub(r'<w:t(?: [^>]*)?>.*?</w:t>', '<w:t/>', xml, flags=re.S)
with ZipFile(new_path) as archive:
    assert archive.testzip() is None
    changed_members = [info.filename for info, data in entries if archive.read(info.filename) != data]
    assert changed_members == ['word/document.xml']
    for name in archive.namelist():
        if name.endswith('.xml') or name.endswith('.rels'):
            ET.fromstring(archive.read(name))
assert all(any(f'STEP{step:02}' in p for p in new_paragraphs) for step in range(1, 15))
result = {
    'source': str(SOURCE),
    'method': 'ZIP-preserving text-only OOXML replacement; python-docx reopen validation',
    'before_sha256': hashlib.sha256(baseline).hexdigest(),
    'after_sha256': hashlib.sha256(new_path.read_bytes()).hexdigest(),
    'before_bytes': len(baseline), 'after_bytes': new_path.stat().st_size,
    'body_paragraphs_before_after': [len(paragraphs), len(new_paragraphs)],
    'tables_before_after': [len(old_doc.tables), len(new_doc.tables)],
    'changes': changes, 'only_changed_package_members': changed_members,
    'formatting_xml_skeleton_unchanged': True,
    'all_other_package_members_byte_identical': True,
    'table_xml_byte_identical': True, 'all_xml_and_relationships_parse': True,
    'zip_test': 'PASS', 'python_docx_reopen': 'PASS',
    'STEP01_through_STEP14_present': True,
    'status': 'STRUCTURAL_PASS_PENDING_VISUAL_RENDER',
}
SOURCE.write_bytes(new_path.read_bytes())
(OUT / 'word-update-validation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({k: v for k, v in result.items() if k != 'changes'}, ensure_ascii=False, indent=2))
