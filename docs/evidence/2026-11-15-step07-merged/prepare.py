from pathlib import Path

here=Path(__file__).resolve().parent
s=(here/'previous-template.py.txt').read_text(encoding='utf-8')
prefix=s[:s.index('\n# STEP07 cart helpers and cases follow.')]
start=s.index("\ntry:\n    check('tested-code-head'")
setup=s[start:s.index('    for port in [8080,8081]:',start)]
footer=s[s.rindex('\nexcept Exception as e:'):]
prefix=prefix.replace("'scope':'STEP07 persistent cart and navigation quantity only; concurrency and faults remain STEP13'","'scope':'Merged STEP07 cart; new full matrix, real guest journey, bounded actor-lock/disable interleaving; no cart/order concurrency or injected fault'")
prefix=prefix.replace("'checks':{},'scope'","'ours_parent_tip':'dda8f8254eec3f63e9c3bede397131cbe55c6179','member_parent_tip':'221dfb6dfa4fe93d69ffe1eecda97e98705406e1','requested_evidence_batch':'2026-11-15-step07-merged','timestamp_policy':'actual system clock; batch directory date is user requested','checks':{},'scope'")
setup=setup.replace("result['branch']=='feat/step07-cart'","result['branch']=='feat/step07-cart-merged'")
setup=setup.replace("['verify_step07.py','verify_browser.cjs','CartWriteProbe.java']","['verify_step07.py','verify_browser.cjs','verify_guest_journey.cjs','CartWriteProbe.java']")
text=prefix+'\n# Merged STEP07 verification helpers follow.\n'+(here/'helpers.pyfrag').read_text(encoding='utf-8')+(here/'journey.pyfrag').read_text(encoding='utf-8')+setup+(here/'cases.pyfrag').read_text(encoding='utf-8')+footer
compile(text,str(here/'verify_step07.py'),'exec')
(here/'verify_step07.py').write_text(text,encoding='utf-8',newline='\n')
print('Merged STEP07 verifier syntax ready; no runtime attempt started')
