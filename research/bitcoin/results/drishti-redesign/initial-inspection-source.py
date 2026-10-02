from playwright.sync_api import sync_playwright
import json,re
from pathlib import Path
out=Path('research/bitcoin/results/drishti-redesign')
with sync_playwright() as p:
 b=p.chromium.launch(headless=True,args=['--no-sandbox','--enable-unsafe-swiftshader'])
 page=b.new_page(viewport={'width':1440,'height':1000},reduced_motion='reduce')
 errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto('http://127.0.0.1:4183/#app',wait_until='networkidle')
 page.screenshot(path=str(out/'globe-first.png'))
 page.get_by_role('navigation').get_by_role('button',name=re.compile('^Map')).click()
 page.get_by_role('heading',name=re.compile('See the flow')).wait_for()
 page.screenshot(path=str(out/'atlas-first.png'),full_page=True)
 print(json.dumps({'errors':errors,'headings':page.get_by_role('heading').all_text_contents(),'buttons':page.get_by_role('button').all_text_contents()[:15],'dimensions':page.evaluate('({width:document.documentElement.scrollWidth,height:document.documentElement.scrollHeight})')}))
 b.close()
