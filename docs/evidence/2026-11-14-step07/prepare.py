from pathlib import Path

here=Path(__file__).resolve().parent
old=here.parent.parent/'step06-admin-images/verification/verify_step06.py'
s=old.read_text(encoding='utf-8')
prefix=s[:s.index('\ndef state():')]
setup_start=s.index('\ntry:\n    check(\'tested-code-head\'')
setup=s[setup_start:s.index('    for port in [8080,8081]:',setup_start)]
footer=s[s.rindex('\nexcept Exception as e:'):]
common=(prefix+ '\n# STEP07 cart helpers and cases follow.\n')
common=common.replace('STEP06','STEP07')
common=common.replace("BASELINE='75e4339266968edc212f160b1119ac720965c408'", "BASELINE='a1d4f3523f557af63fc77ea883986c099edcd93e'")
common=common.replace('STEP07 product images only', 'STEP07 persistent cart and navigation quantity only')
common=common.replace("404 if port==8080 else 200",'200')
common=common.replace("def launch(app,port):\n    log=BASE/(app+'.log');h=log.open('wb');handles.append(h)","launch_counts={}\ndef launch(app,port,profile='default'):\n    launch_counts[app]=launch_counts.get(app,0)+1\n    log=BASE/(app+'-'+profile+'-'+str(launch_counts[app])+'.log');h=log.open('wb');handles.append(h)")
common=common.replace("'--server.address=127.0.0.1']", "'--server.address=127.0.0.1','--spring.profiles.active='+profile]")
common=common.replace("'password_supplied':True,'argv'", "'password_supplied':True,'profile':profile,'argv'")
setup=setup.replace('STEP06','STEP07').replace('feat/step06-admin-images','feat/step07-cart')
setup=setup.replace("'--','csucampuscraft-admin'", "'--','csucampuscraft-user'")
setup=setup.replace("['verify_step06.py','verify_browser.cjs','AlbumWriteProbe.java']", "['verify_step07.py','verify_browser.cjs','CartWriteProbe.java']")
setup=setup.replace("GRANT INSERT,UPDATE,DELETE ON csucampuscraft.product_image", "GRANT INSERT,UPDATE,DELETE ON csucampuscraft.cart_item")
setup=setup.replace('    sql("GRANT UPDATE ON csucampuscraft.product TO \'csucampuscraft\'@\'127.0.0.1\';")\n','')
footer=footer.replace('STEP06','STEP07')
text=common+(here/'helpers.pyfrag').read_text(encoding='utf-8')+setup+(here/'cases.pyfrag').read_text(encoding='utf-8')+footer
compile(text,str(here/'verify_step07.py'),'exec')
(here/'verify_step07.py').write_text(text,encoding='utf-8',newline='\n')
print('STEP07 verifier assembled; syntax PASS; no runtime attempt started')
