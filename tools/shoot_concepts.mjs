/* tools/shoot_concepts.mjs — the screenshots behind /admin/concepts/.
 *
 * WHY A TOOL AND NOT A ONE-OFF. The concepts page is a critique, and a critique
 * whose evidence cannot be regenerated is an opinion. This produces every image
 * on that page from the mirror in data/concepts/ plus this repository's own
 * docs/, so a reader who doubts a comparison can re-run it and get the same
 * bytes rather than taking a screenshot on trust.
 *
 * IT DOES NOT TOUCH THE NETWORK. The concept pages were fetched once by
 * tools/promote_concepts.py, hashed, and committed under data/concepts/mirror/.
 * This serves that directory and docs/ on loopback and drives Chromium at both.
 * That is deliberate: the concepts live on somebody else's host and could change
 * or vanish, and a comparison page that silently re-renders against a moved
 * target is worse than no comparison at all.
 *
 * NOT IN admin/build/validate.sh, for the same reason as tools/walkthrough.mjs:
 * the gate is Python and `node --check` with nothing installed, and this needs a
 * browser. Run it by hand when the mirror or the homepage changes:
 *
 *     python3 build.py && node tools/shoot_concepts.mjs
 *
 * Set PW to the Playwright entry point if it is not on the default path.
 */
const PW = process.env.PW || '/opt/node22/lib/node_modules/playwright/index.mjs';
const { chromium } = await import(PW);
import http from 'node:http'; import fs from 'node:fs'; import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const DOCS = path.join(HERE, '..', 'docs');
const MIRROR = path.join(HERE, '..', 'data', 'concepts', 'mirror');
const OUT = path.join(HERE, '..', 'assets', 'shots', 'concepts');

const T = { '.html':'text/html', '.js':'text/javascript', '.css':'text/css',
            '.json':'application/json', '.svg':'image/svg+xml', '.png':'image/png',
            '.jpg':'image/jpeg', '.md':'text/plain', '.txt':'text/plain' };
function serve(root, port) {
  const s = http.createServer((q, r) => {
    let u = decodeURIComponent(q.url.split('?')[0]);
    let f = path.join(root, u);
    if (fs.existsSync(f) && fs.statSync(f).isDirectory()) f = path.join(f, 'index.html');
    if (!fs.existsSync(f) && fs.existsSync(f + '.html')) f = f + '.html';
    if (!fs.existsSync(f)) { r.writeHead(404); return r.end('404 ' + u); }
    r.writeHead(200, { 'content-type': T[path.extname(f)] || 'text/plain' });
    r.end(fs.readFileSync(f));
  });
  return new Promise(res => s.listen(port, () => res(s)));
}

// The four homepages. `current` is this repository's build; the other three are
// the mirror. Same viewport, same wait, same encoder — the only variable is the
// page, which is the whole point of putting them beside each other.
const PAGES = [
  ['current',     'http://127.0.0.1:8841/'],
  ['marketplace', 'http://127.0.0.1:8842/index.html'],
  ['guided',      'http://127.0.0.1:8842/guided.html'],
  ['studio',      'http://127.0.0.1:8842/studio.html'],
];

// JPEG, because every one of these is mostly photographic hero artwork and a
// lossless encoding of it is megabytes per image in a repository that is read
// far more often than it is cloned. The card crops stay PNG: they are type on
// a flat ground, which is exactly where JPEG ringing shows.
const DESKTOP = { width: 1200, height: 750 };
const MOBILE  = { width: 390,  height: 780 };

await serve(DOCS, 8841);
await serve(MIRROR, 8842);
fs.mkdirSync(OUT, { recursive: true });

const br = await chromium.launch();
const wrote = [];
async function shoot(file, opts, fn) {
  const ctx = await br.newContext(opts.ctx);
  const p = await ctx.newPage();
  await p.goto(opts.url, { waitUntil: 'networkidle', timeout: 60000 });
  await p.waitForTimeout(700);
  await fn(p, file);
  await ctx.close();
  const kb = Math.round(fs.statSync(path.join(OUT, file)).size / 1024);
  wrote.push(`${file} ${kb}KB`);
}

for (const [name, url] of PAGES) {
  await shoot(`${name}-desktop.jpg`, { url, ctx: { viewport: DESKTOP } },
    (p, f) => p.screenshot({ path: path.join(OUT, f), type: 'jpeg', quality: 78 }));
  await shoot(`${name}-desktop-full.jpg`, { url, ctx: { viewport: DESKTOP } },
    (p, f) => p.screenshot({ path: path.join(OUT, f), type: 'jpeg', quality: 72, fullPage: true }));
  await shoot(`${name}-mobile.jpg`, { url, ctx: { viewport: MOBILE } },
    (p, f) => p.screenshot({ path: path.join(OUT, f), type: 'jpeg', quality: 78 }));
}

// The price ladder, cropped to itself on both sides. This is the comparison the
// page actually argues from, so it is captured as an element rather than as a
// scroll position that drifts the next time a paragraph above it grows.
// ELEMENT CAPTURE, NOT A VIEWPORT CLIP. A clip was the first attempt and it was
// wrong twice over: the sticky header painted over the top of the cards, and the
// cards are taller than any fixed height once the column narrows, so the grey
// "no payment link" boxes — the single most important thing in the comparison —
// fell off the bottom while the caption went on describing them.
await shoot('cards-current.png', { url: 'http://127.0.0.1:8841/', ctx: { viewport: DESKTOP } },
  async (p, f) => {
    const el = await p.$('.skus');
    await el.screenshot({ path: path.join(OUT, f) });
  });
await shoot('cards-marketplace.png', { url: 'http://127.0.0.1:8842/index.html', ctx: { viewport: DESKTOP } },
  async (p, f) => {
    const el = await p.$('#products');
    await el.screenshot({ path: path.join(OUT, f) });
  });

await br.close();
console.log('shoot_concepts: ' + wrote.length + ' images →  assets/shots/concepts/');
for (const w of wrote) console.log('  ' + w);
process.exit(0);
