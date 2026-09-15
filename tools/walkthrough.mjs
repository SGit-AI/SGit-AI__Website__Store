/* tools/walkthrough.mjs — runs EXACTLY the assertions printed on /admin/try/.
 *
 * The walkthrough page tells a synthetic user to assert forty-six things. A page
 * that tells somebody to check something that is not true is worse than a page
 * that says nothing, so the assertions are also a script, and the script is what
 * was run before the page was written.
 *
 * It is NOT in admin/build/validate.sh. The gate is Python and `node --check`
 * with no installed dependencies, and this needs a browser — putting Playwright
 * in the release path would make every release depend on a download. Run it by
 * hand when the cart, the discount or the handover changes:
 *
 *     python3 build.py
 *     node tools/walkthrough.mjs
 *
 * It serves docs/ on 127.0.0.1 and drives Chromium against it. Nothing it does
 * touches the network: the one thing it will not do is follow the handover to
 * riskmandate.ai, because that is their page and this is a test of ours.
 *
 * Set PW to the Playwright entry point if it is not on the default path.
 */
const PW = process.env.PW || '/opt/node22/lib/node_modules/playwright/index.mjs';
const { chromium } = await import(PW);
import http from 'node:http'; import fs from 'node:fs'; import path from 'node:path';
const ROOT = new URL('../docs/', import.meta.url).pathname;
const T={'.html':'text/html','.js':'text/javascript','.css':'text/css','.json':'application/json','.svg':'image/svg+xml','.png':'image/png','.md':'text/plain','.txt':'text/plain'};
const srv=http.createServer((q,s)=>{let u=decodeURIComponent(q.url.split('?')[0]);let f=path.join(ROOT,u);
 if(fs.existsSync(f)&&fs.statSync(f).isDirectory())f=path.join(f,'index.html');
 if(!fs.existsSync(f)){s.writeHead(404);return s.end('404 '+u);}
 s.writeHead(200,{'content-type':T[path.extname(f)]||'text/plain'});s.end(fs.readFileSync(f));});
await new Promise(r=>srv.listen(8991,r));
const B='http://127.0.0.1:8991';
const br=await chromium.launch(); const ctx=await br.newContext();
const p=await ctx.newPage();
let pass=0, fail=0;
const A=(name,ok,got)=>{ if(ok){pass++; console.log('  ok   '+name);} else {fail++; console.log('  FAIL '+name+'  got: '+JSON.stringify(got));} };
const offsite=[];
p.on('request',r=>{ const u=new URL(r.url()); if(u.origin!==B) offsite.push(r.url()); });

console.log('1 catalogue with SYNTH4DELTA');
await p.goto(B+'/policies/?code=SYNTH4DELTA'); await p.waitForTimeout(250);
A('.codebar .cb-chip contains 100% off', (await p.locator('.codebar .cb-chip').innerText()).includes('100% off'));
A("location.search has no 'code='", !(await p.evaluate(()=>location.search)).includes('code='), await p.evaluate(()=>location.search));
A("localStorage['sgit.store.code.v1'] === 'synth-agent'", await p.evaluate(()=>localStorage['sgit.store.code.v1'])==='synth-agent');

console.log('2 the shape page');
await p.goto(B+'/p/gmail-readonly/'); await p.waitForTimeout(200);
A('.lvl length === 4', await p.locator('.lvl').count()===4);
const prices = await p.locator('.lvl-price').allInnerTexts();
A("prices are ['£5','£50','£500','£1,500']", JSON.stringify(prices)===JSON.stringify(['£5','£50','£500','£1,500']), prices);
const skus = await p.locator('.lvl-sku').allInnerTexts();
A('every sku matches /^ABP-[A-Z0-9]{3}-[PVCS]$/', skus.every(s=>/^ABP-[A-Z0-9]{3}-[PVCS]$/.test(s)), skus);

console.log('3 add two levels');
await p.locator('.lvl').nth(0).locator('button:has-text("Add to order")').click();
await p.locator('.lvl').nth(2).locator('button:has-text("Add to order")').click();
const order = await p.evaluate(()=>JSON.parse(localStorage['sgit.store.order.v1']));
A('order has two item keys', Object.keys(order.items).length===2, Object.keys(order.items));

console.log('4 the cart');
await p.goto(B+'/cart/'); await p.waitForTimeout(200);
A(".ct-sum reads '£0'", (await p.locator('.ct-sum').innerText()).trim()==='£0', await p.locator('.ct-sum').innerText());
const off = await p.locator('.ct-off').innerText();
A('.ct-off names the discount and its percentage', /Synthetic run/.test(off) && /100%/.test(off), off);
const ref = (await p.locator('.ob-ref').innerText()).trim();
A('.ob-ref matches the reference alphabet', /^SG-[23456789ABCDEFGHJKLMNPQRSTUVWXYZ]{6}$/.test(ref), ref);

console.log('5 paying');
await p.goto(B+'/pay/'); await p.waitForTimeout(200);
A(".ps-now reads '£0'", (await p.locator('.ps-now').innerText()).trim()==='£0');
A('exactly one .rail-sim', await p.locator('.rail-sim').count()===1);
A("the .rail-flag textContent is 'Simulated — charges nothing'", (await p.locator('.rail-sim .rail-flag').evaluate(e=>e.textContent))==='Simulated \u2014 charges nothing', await p.locator('.rail-sim .rail-flag').evaluate(e=>e.textContent));
await p.locator('.rail-sim button.buy').click();

console.log('6 what happens now');
await p.waitForURL('**/order/**',{timeout:6000}); await p.waitForTimeout(250);
A('.oh-ref equals the cart reference', (await p.locator('.oh-ref').innerText()).trim()===ref);
A('.aftercard length === 2', await p.locator('.aftercard').count()===2);
const hrefs = await p.locator('.ac-go a').evaluateAll(a=>a.map(x=>x.getAttribute('href')));
const RX = /^https:\/\/riskmandate\.ai\/paid-t[1-4]\.html\?order=SG-[A-Z0-9]{6}(&shape=[a-z0-9-]+)?$/;
A('every handover href matches the contract', hrefs.length===2 && hrefs.every(h=>RX.test(h)), hrefs);
A('the level-1 link carries &shape=gmail-readonly', hrefs.some(h=>h.includes('paid-t1')&&h.includes('&shape=gmail-readonly')), hrefs);
A('the level-3 link carries no shape', hrefs.some(h=>h.includes('paid-t3')&&!h.includes('shape=')), hrefs);
const body = await p.evaluate(()=>document.documentElement.outerHTML);
A('no sgit_private_ string on the page', !/sgit_private_(vault|write|read)_/.test(body));

console.log('the three invariants, on every page touched');
for (const u of ['/','/policies/','/p/gmail-readonly/','/cart/','/pay/','/order/','/admin/try/','/paying/','/ledger/']) {
  await p.goto(B+u); await p.waitForTimeout(120);
  const n = await p.evaluate(()=>document.querySelectorAll('form,input,textarea,select').length);
  A('NO FORM on '+u, n===0, n);
  const keys = await p.evaluate(()=>/sgit_private_(vault|write|read)_[A-Za-z0-9]{6,}/.test(document.documentElement.outerHTML));
  A('NO KEY on '+u, keys===false);
}
A('NO NETWORK — nothing left the origin', offsite.length===0, offsite);

console.log('mode 2 — fetch-only checks');
const idx = await (await fetch(B+'/assets/site-index.json')).json();
const byId = Object.fromEntries(idx.offers.map(o=>[o.id,o]));
A('site-index prices', ['£5','£50','£500','£1,500'].every((v,i)=>byId['t'+(i+1)].price===v), [1,2,3,4].map(i=>byId['t'+i].price));
A('site-index split 100/100/20/20', [100,100,20,20].every((v,i)=>byId['t'+(i+1)].pay_now_pct===v), [1,2,3,4].map(i=>byId['t'+i].pay_now_pct));
const cartHtml = await (await fetch(B+'/cart/')).text();
const model = JSON.parse(cartHtml.match(/<script type="application\/json" id="shop-model">(.*?)<\/script>/s)[1]);
A('every rail url is empty', model.rails.every(r=>!r.url), model.rails.map(r=>r.url));
A('exactly one rail is simulated', model.rails.filter(r=>r.simulated).length===1);
A("codes carry a 64-hex hash and no 'code'", model.codes.every(c=>/^[0-9a-f]{64}$/.test(c.hash) && !('code' in c)));
A('every level has post_url paid-t<n>', model.levels.every((l,i)=>l.post_url==='https://riskmandate.ai/paid-t'+(i+1)+'.html'), model.levels.map(l=>l.post_url));
A("post_carries is ['order'] plus 'shape' at level one", JSON.stringify(model.levels.map(l=>l.post_carries))===JSON.stringify([['order','shape'],['order'],['order'],['order']]), model.levels.map(l=>l.post_carries));
A('the model has 16 shapes', model.shapes.length===16, model.shapes.length);

console.log('\n'+pass+' passed, '+fail+' failed');
await br.close(); srv.close(); process.exit(fail?1:0);
