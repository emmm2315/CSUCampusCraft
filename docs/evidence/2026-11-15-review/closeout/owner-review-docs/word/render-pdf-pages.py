"""Rasterize native Word PDFs with bundled PDFium; retain hashes for QA."""
import hashlib
import json
from pathlib import Path
import pypdfium2 as pdfium
from pypdf import PdfReader

ROOT = Path('D:/Github Projects/CSUCampusCraft/docs/evidence/2026-11-15-review/closeout/owner-review-docs/word')
report = {'renderer': 'Microsoft Word 16 COM PDF -> bundled pypdfium2 PNG', 'dpi': 144, 'phases': {}}
for phase in ('before', 'after'):
    source = ROOT / '_qa' / f'{phase}.pdf'
    doc = pdfium.PdfDocument(str(source))
    target = ROOT / '_qa' / phase
    target.mkdir(exist_ok=True)
    text = PdfReader(source)
    entries = []
    for index in range(len(doc)):
        page = doc[index]
        bitmap = page.render(scale=2)
        image = bitmap.to_pil()
        path = target / f'page-{index + 1}.png'
        image.save(path)
        entries.append({'page': index + 1, 'width': image.width, 'height': image.height, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'pixel_sha256': hashlib.sha256(image.tobytes()).hexdigest(), 'pdf_text_sha256': hashlib.sha256((text.pages[index].extract_text() or '').encode()).hexdigest()})
    report['phases'][phase] = {'pdf_bytes': source.stat().st_size, 'page_count': len(doc), 'pages': entries}
assert report['phases']['before']['page_count'] == report['phases']['after']['page_count'] == 19
report['changed_pages'] = [b['page'] for a, b in zip(report['phases']['before']['pages'], report['phases']['after']['pages']) if a['pixel_sha256'] != b['pixel_sha256']]
report['unchanged_pages'] = [b['page'] for a, b in zip(report['phases']['before']['pages'], report['phases']['after']['pages']) if a['pixel_sha256'] == b['pixel_sha256']]
(ROOT / 'word-render-comparison.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps({k: v for k, v in report.items() if k != 'phases'}))
