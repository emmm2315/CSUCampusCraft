"""New bundled-PDFium rendering for Word COM output; QA files stay private."""
import argparse
import hashlib
import json
import pathlib
import pypdfium2 as pdfium

parser=argparse.ArgumentParser()
parser.add_argument('pdf',type=pathlib.Path)
parser.add_argument('--out',type=pathlib.Path,required=True)
parser.add_argument('--metadata-only',action='store_true')
args=parser.parse_args()
args.out.mkdir(parents=True,exist_ok=True)
doc=pdfium.PdfDocument(str(args.pdf))
pages=[]
try:
    for index in range(len(doc)):
        page=doc[index]
        bitmap=page.render(scale=2)
        image=bitmap.to_pil()
        record={'page':index+1,'width':image.width,'height':image.height,'pixel_sha256':hashlib.sha256(image.tobytes()).hexdigest()}
        if not args.metadata_only:
            target=args.out/f'page-{index+1:02}.png';image.save(target)
            record['path']=target.name
            record['png_sha256']=hashlib.sha256(target.read_bytes()).hexdigest()
        pages.append(record)
        image.close();bitmap.close();page.close()
finally:doc.close()
result={'renderer':'Microsoft Word COM 16.0 PDF followed by bundled pypdfium2 at 144 dpi','pdf_sha256':hashlib.sha256(args.pdf.read_bytes()).hexdigest(),'page_count':len(pages),'pages':pages,'metadata_only':args.metadata_only}
(args.out/'pages.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'overall':'PASS','page_count':len(pages),'metadata':str(args.out/'pages.json')}))
