/* tools/shoot_v3.mjs — the v3 product artwork, re-encoded to a committable size.
 *
 * The four renders arrive as 1.9–2.1MB PNGs, 7.9MB for the set. They are
 * photographic product art with soft gradients — the worst possible case for a
 * lossless encoding and the best possible case for JPEG. At the size a card
 * actually shows them (280px, so 560 for a 2× screen) the set comes down to
 * about a twentieth of that with nothing visible lost.
 *
 * WHY A BROWSER. There is no image library on this machine — no Pillow, no
 * ImageMagick. Chromium is here for the screenshot tools, and it is a perfectly
 * good encoder: draw the PNG to a canvas at the target width and read it back as
 * JPEG. That is an honest re-encode rather than a crop.
 *
 * NOT IN admin/build/validate.sh, like every other tool here that needs a
 * browser. Run it by hand after tools/promote_v3.py:
 *
 *     python3 tools/promote_v3.py && node tools/shoot_v3.mjs
 *
 * It writes assets/next/art/*.jpg and records each one's source hash, width and
 * bytes in data/next/artwork.json, so a re-encode can always be traced back to
 * the PNG that arrived.
 */
const PW = process.env.PW || '/opt/node22/lib/node_modules/playwright/index.mjs';
const { chromium } = await import(PW);
import fs from 'node:fs'; import path from 'node:path'; import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.join(HERE, '..');
const SRC = path.join(ROOT, 'data', 'next', 'mirror', 'assets');
const OUT = path.join(ROOT, 'assets', 'next', 'art');

// 720 wide: a card shows these at 280css and the product page at ~620css, so 720
// covers the largest use at 1× and the card at 2× without carrying a hero-sized
// file for a thumbnail.
const WIDTH = 720;
const QUALITY = 0.82;

const JOBS = [
  ['marketplace.png',          'pack.jpg',     'ABP Pack'],
  ['vault-marketplace.png',    'vault.jpg',    'ABP Vault'],
  ['toolkit-marketplace.png',  'tailored.jpg', 'ABP Tailored'],
  ['reviewed-marketplace.png', 'reviewed.jpg', 'ABP Reviewed'],
];

fs.mkdirSync(OUT, { recursive: true });
const br = await chromium.launch();
const ctx = await br.newContext();
const page = await ctx.newPage();
const records = [];

for (const [src, dest, label] of JOBS) {
  const raw = fs.readFileSync(path.join(SRC, src));
  const dataUri = 'data:image/png;base64,' + raw.toString('base64');
  const out = await page.evaluate(async ({ uri, width, quality }) => {
    const img = new Image();
    await new Promise((res, rej) => { img.onload = res; img.onerror = rej; img.src = uri; });
    const scale = Math.min(1, width / img.naturalWidth);
    const c = document.createElement('canvas');
    c.width = Math.round(img.naturalWidth * scale);
    c.height = Math.round(img.naturalHeight * scale);
    const g = c.getContext('2d');
    g.imageSmoothingQuality = 'high';
    g.drawImage(img, 0, 0, c.width, c.height);
    return { data: c.toDataURL('image/jpeg', quality),
             w: c.width, h: c.height,
             from: [img.naturalWidth, img.naturalHeight] };
  }, { uri: dataUri, width: WIDTH, quality: QUALITY });

  const buf = Buffer.from(out.data.split(',')[1], 'base64');
  fs.writeFileSync(path.join(OUT, dest), buf);
  records.push({
    file: dest, label,
    from: src,
    source_sha256: crypto.createHash('sha256').update(raw).digest('hex'),
    source_bytes: raw.length,
    source_size: out.from.join('×'),
    size: [out.w, out.h].join('×'),
    bytes: buf.length,
    quality: QUALITY,
  });
  console.log(`shoot_v3: ${dest.padEnd(13)} ${out.from.join('×').padEnd(11)} → ` +
              `${[out.w, out.h].join('×').padEnd(9)}  ` +
              `${Math.round(raw.length / 1024)}KB → ${Math.round(buf.length / 1024)}KB`);
}

fs.writeFileSync(path.join(ROOT, 'data', 'next', 'artwork.json'), JSON.stringify({
  _what_this_is:
    'The v3 product artwork as this site ships it: the mirrored PNGs re-encoded to ' +
    'JPEG at a size a card actually uses. Written by tools/shoot_v3.mjs, never by ' +
    'hand — source_sha256 ties each file back to the PNG that arrived.',
  _how_to_refresh: 'python3 tools/promote_v3.py && node tools/shoot_v3.mjs',
  width: WIDTH, quality: QUALITY,
  art: records,
}, null, 2) + '\n');

const total = records.reduce((a, r) => a + r.bytes, 0);
const before = records.reduce((a, r) => a + r.source_bytes, 0);
console.log(`shoot_v3: ${Math.round(before / 1024)}KB → ${Math.round(total / 1024)}KB ` +
            `(${Math.round(100 - total / before * 100)}% smaller)`);
await br.close();
process.exit(0);
