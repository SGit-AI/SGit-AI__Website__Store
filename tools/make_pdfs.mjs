/* tools/make_pdfs.mjs — the printable forms, rendered from the built pages.
 *
 * "This would also make really good brochures and PDFs." The comparison table is
 * the one page here whose whole value is seeing five columns at once — which a
 * phone cannot give and a sheet of A4 can. So the brochure is a BUILD TARGET
 * rather than a second document: this renders the real page through the real
 * print stylesheet, so a row added to data/comparison.yml is in the PDF on the
 * next run and nothing is ever retyped into a second artefact.
 *
 * NOT IN admin/build/validate.sh, for the same reason as walkthrough.mjs and
 * shoot_concepts.mjs: the gate is Python and `node --check` with nothing
 * installed, and this needs a browser. Run it by hand when the table or the
 * print rules change:
 *
 *     python3 build.py && node tools/make_pdfs.mjs
 *
 * IT WRITES ITS OWN PROVENANCE. data/downloads.json records the version each
 * file was rendered from, its bytes and its sha256. check_site asserts the file
 * on disk still matches that hash and that the version is one this site has
 * really released, and NOTES — rather than fails — when a PDF lags the current
 * release. A brochure that silently disagrees with the page is worse than none;
 * a brochure that is four releases old and says so is fine.
 *
 * Set PW to the Playwright entry point if it is not on the default path.
 */
const PW = process.env.PW || '/opt/node22/lib/node_modules/playwright/index.mjs';
const { chromium } = await import(PW);
import http from 'node:http'; import fs from 'node:fs'; import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.join(HERE, '..');
const DOCS = path.join(ROOT, 'docs');
const OUT  = path.join(ROOT, 'assets', 'downloads');

const version = fs.readFileSync(path.join(ROOT, 'admin', 'build', 'version.txt'), 'utf8').trim();

const T = { '.html':'text/html', '.js':'text/javascript', '.css':'text/css',
            '.json':'application/json', '.svg':'image/svg+xml', '.png':'image/png',
            '.jpg':'image/jpeg', '.md':'text/plain', '.txt':'text/plain' };
const srv = http.createServer((q, r) => {
  let u = decodeURIComponent(q.url.split('?')[0]);
  let f = path.join(DOCS, u);
  if (fs.existsSync(f) && fs.statSync(f).isDirectory()) f = path.join(f, 'index.html');
  if (!fs.existsSync(f)) { r.writeHead(404); return r.end('404 ' + u); }
  r.writeHead(200, { 'content-type': T[path.extname(f)] || 'text/plain' });
  r.end(fs.readFileSync(f));
});
await new Promise(r => srv.listen(8951, r));

// One entry per printable. `landscape` has to agree with the @page rule in the
// stylesheet — Chromium takes the CSS size when it is given one, and passing a
// contradicting flag here is how you get a silently cropped table.
const JOBS = [
  { url: '/compare/', file: 'abp-comparison.pdf', landscape: true,
    title: 'What each level actually gets you' },
];

const br = await chromium.launch();
fs.mkdirSync(OUT, { recursive: true });
const records = [];

for (const j of JOBS) {
  const ctx = await br.newContext({ viewport: { width: 1280, height: 900 } });
  const p = await ctx.newPage();
  await p.goto('http://127.0.0.1:8951' + j.url, { waitUntil: 'networkidle', timeout: 60000 });
  await p.emulateMedia({ media: 'print' });
  await p.waitForTimeout(400);

  // A table that overflows the printed page loses its right-hand columns with no
  // warning at all, so measure before committing the file.
  const fits = await p.evaluate(() => {
    // THE TABLE HAS TWO CLASSES BECAUSE THE SITE HAS TWO DESIGNS ON IT: .n-cmp is
    // the store's, .cmpt is the one kept at /v1/. Naming both means this keeps
    // working whichever page it is pointed at, and stops silently when it is
    // pointed at a page with no table at all — which is what happened the day the
    // designs swapped.
    const t = document.querySelector('table.n-cmp, table.cmpt');
    if (!t) return { ok: false, why: 'no comparison table on the page' };
    const over = t.scrollWidth > t.clientWidth + 1;
    return { ok: !over, why: over ? `table overflows: ${t.scrollWidth} > ${t.clientWidth}` : '',
             cols: t.querySelectorAll('thead th').length,
             rows: t.querySelectorAll('tbody tr').length };
  });
  if (!fits.ok) { console.error(`make_pdfs: ${j.url} — ${fits.why}`); process.exit(1); }

  const dest = path.join(OUT, j.file);
  await p.pdf({ path: dest, format: 'A4', landscape: j.landscape,
                printBackground: true, preferCSSPageSize: true });
  await ctx.close();

  const buf = fs.readFileSync(dest);
  records.push({ file: j.file, url: j.url, title: j.title,
                 bytes: buf.length,
                 sha256: crypto.createHash('sha256').update(buf).digest('hex'),
                 version, generated: new Date().toISOString().slice(0, 10),
                 columns: fits.cols, rows: fits.rows });
  console.log(`make_pdfs: ${j.file}  ${Math.round(buf.length/1024)}KB  ` +
              `${fits.cols} columns, ${fits.rows} rows, from ${version}`);
}

fs.writeFileSync(path.join(ROOT, 'data', 'downloads.json'), JSON.stringify({
  _what_this_is:
    'The printable forms, and what each one was rendered from. Written by ' +
    'tools/make_pdfs.mjs, never by hand — the hash is what makes a PDF that has ' +
    'drifted from the page impossible to miss.',
  _how_to_refresh: 'python3 build.py && node tools/make_pdfs.mjs',
  downloads: records,
}, null, 2) + '\n');

await br.close();
process.exit(0);
