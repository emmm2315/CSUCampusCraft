from pathlib import Path
root=Path(__file__).resolve().parents[2]
here=Path(__file__).resolve().parent
old=(root/'step05-admin-catalog/verification/verify_step05.py').read_text(encoding='utf-8-sig')
prefix=old[:old.index('def catalog_state():')].replace('STEP05','STEP06').replace('step05','step06').replace('feat/step06-admin-catalog','feat/step06-admin-images').replace('a8438b72493fba108577e0ba4918e61b043b8916','75e4339266968edc212f160b1119ac720965c408')
prefix=prefix.replace("'scope':'STEP06 management categories/products/restock; isolated real MySQL + HTTP, no concurrency/fault injection'", "'scope':'STEP06 product images, isolated real MySQL + dual JAR HTTP, no concurrency/fault injection'")
prefix=prefix.replace("'scope':'STEP06 admin category/product/replenishment only; concurrency and faults remain STEP13'", "'scope':'STEP06 product images only; concurrency and faults remain STEP13'")
prefix=prefix.replace("        try:r=self.opener.open(req,timeout=12)","        post_before=snapshot() if method=='POST' else None\n        post_state=state() if method=='POST' else None\n        try:r=self.opener.open(req,timeout=12)")
prefix=prefix.replace("        return r.code,h,body,dom", "        if method=='POST':snapshot_pair('http-post-'+str(http_no),post_before,post_state,snapshot(),state(),http_sequence=http_no,path=path,status=r.code,automatic_all_posts=True)\n        return r.code,h,body,dom")
(here/'verify_step06.py').write_text(prefix+(here/'cases.pyfrag').read_text(encoding='utf-8'),encoding='utf-8',newline='\n')
