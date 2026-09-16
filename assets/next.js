/* assets/next.js — behaviour for the next store.
 * ============================================================================
 *
 * WHAT THIS DOES. Three switches, one listener, no framework:
 *   · the level switcher on the product page      (which of the four you buy)
 *   · the audience switcher                        (the same product, your role)
 *   · the media tabs                               (artwork / contents / the empty slot)
 *
 * WHERE THE DATA COMES FROM. A JSON island in the page, written by build.py out
 * of data/offers.yml and data/audiences.yml. Nothing here has a price, a name or
 * a delivery estimate in it: this file knows how to swap regions and the page
 * knows what the regions say. That is what keeps a number from existing twice —
 * and the release gate parses every island, so a malformed one fails the build
 * rather than the page.
 *
 * WHAT IT DELIBERATELY DOES NOT DO.
 *   · No network. The store opens no connection; a check enforces it.
 *   · No storage. Nothing here is remembered between visits.
 *   · No forms. There is no input, textarea or select anywhere in this site's
 *     output and a check holds that line — so every control is a button.
 *   · No framework, no build step. It is read as often as it is run.
 *
 * STATE LIVES IN THE URL. ?level=2 and ?audience=founder are the whole of it, so
 * a reader can send somebody the exact thing they are looking at. replaceState,
 * not pushState: switching a level is not a new page in anybody's history.
 */
(function () {
  'use strict';

  /* ---------------------------------------------------------------- data -- */

  function island(id) {
    var el = document.getElementById(id);
    if (!el) return null;
    try {
      return JSON.parse(el.textContent);
    } catch (e) {
      // A malformed island means the page is wrong, not the reader. Say so in
      // the console and leave the server-rendered markup exactly as it is —
      // every switch below degrades to "the page you were served".
      console.error('[next] could not read #' + id, e);
      return null;
    }
  }

  var MODEL = island('next-model');
  if (!MODEL) return;

  var LEVELS = MODEL.levels || [];
  var AUDIENCES = MODEL.audiences || [];
  var SHAPES = MODEL.shapes || [];

  /* WHICH POLICY THE PRODUCT PAGE IS SELLING. It comes off the address, and it
     is the site's default until somebody changes it — the page says which,
     because a default that looks like a choice is a wrong order. A slug the
     build does not know falls back to the default rather than to a blank. */
  var currentPolicy = (function () {
    var want = new URLSearchParams(location.search).get('policy');
    var hit = null;
    for (var i = 0; i < SHAPES.length; i++) {
      if (SHAPES[i].slug === want && SHAPES[i].pickable !== false) hit = SHAPES[i];
    }
    if (!hit) for (var j = 0; j < SHAPES.length; j++) {
      if (SHAPES[j].slug === MODEL.default_policy) hit = SHAPES[j];
    }
    return hit;
  }());

  /* ------------------------------------------------------------- helpers -- */

  function byId(id) { return document.getElementById(id); }

  /** Set text on an element if the page has one. Pages share this script and
   *  carry different regions, so a missing id is normal rather than an error. */
  function setText(id, value) {
    var el = byId(id);
    if (el && value != null) el.textContent = value;
  }

  function setAttr(id, name, value) {
    var el = byId(id);
    if (el && value != null) el.setAttribute(name, value);
  }

  /** Mark exactly one button in a group as pressed. aria-pressed is the state:
   *  the stylesheet reads it, so there is no second source of truth. */
  function press(attr, value) {
    var all = document.querySelectorAll('[' + attr + ']');
    for (var i = 0; i < all.length; i++) {
      all[i].setAttribute('aria-pressed',
        String(all[i].getAttribute(attr) === String(value)));
    }
  }

  function replaceList(id, items) {
    var el = byId(id);
    if (!el) return;
    var frag = document.createDocumentFragment();
    (items || []).forEach(function (text) {
      var li = document.createElement('li');
      li.textContent = text;
      frag.appendChild(li);
    });
    el.replaceChildren(frag);
  }

  function setUrlParam(key, value) {
    if (!window.history || !history.replaceState) return;
    try {
      var url = new URL(location.href);
      url.searchParams.set(key, value);
      history.replaceState(null, '', url);
    } catch (e) { /* a URL we cannot parse is not worth failing a switch over */ }
  }

  /* ------------------------------------------------------- level switcher -- */

  var currentLevel = null;

  function selectLevel(id, updateUrl) {
    var level = null;
    for (var i = 0; i < LEVELS.length; i++) {
      if (LEVELS[i].id === id) { level = LEVELS[i]; break; }
    }
    if (!level || level.id === currentLevel) return;
    currentLevel = level.id;

    press('data-level', level.id);

    setText('p-name', level.short_name);
    setText('p-sub', level.short_sub);
    setText('p-code', level.code);
    setText('p-spec-code', level.code);
    setText('p-price', level.price);
    setText('p-clock', level.clock);
    setText('p-spec-clock', level.clock);
    setText('p-what', level.what);
    setText('p-buy-name', level.short_name);

    // The deposit line only exists on the two levels that take one. Hiding it
    // is not enough — an empty element still takes a margin — so the region is
    // [hidden], which the stylesheet turns off entirely.
    var split = byId('p-split');
    if (split) {
      split.hidden = !level.split;
      if (level.split) split.textContent = level.split;
    }

    // The button adds a line — this policy at this level — to the order the
    // browser is holding. The second block on this page owns the order and
    // handles the click; this one only keeps the button pointed at the right
    // line and saying the right name.
    var buy = byId('p-buy');
    if (buy && currentPolicy) {
      buy.textContent = 'Add ABP ' + level.short_name + ' to your order →';
      buy.setAttribute('data-add-line', currentPolicy.slug + '|' + level.cart_id);
    }
    var added = byId('p-added');
    if (added) added.hidden = true;

    var claim = byId('p-claim');
    if (claim && level.claim) {
      // the arrow is part of the chip: it says the chip is a link to the
      // ledger entry, and dropping it on a switch made it look like a label
      claim.textContent = level.state_label + ' \u2197';
      claim.className = 'n-claim n-claim--' + level.state;
      claim.href = (MODEL.ledger_url || '/ledger/') + '#claim-' + level.claim;
    }

    var art = byId('p-art');
    if (art && level.art) {
      art.src = level.art;
      art.alt = level.short_name + ' — concept artwork for a digital deliverable';
    }

    replaceList('p-included', level.included);
    replaceList('p-excluded', level.excluded);

    if (updateUrl !== false) setUrlParam('level', level.id);
  }

  /* ---------------------------------------------------- audience switcher -- */

  var currentAudience = null;

  function selectAudience(id, updateUrl) {
    var audience = null;
    for (var i = 0; i < AUDIENCES.length; i++) {
      if (AUDIENCES[i].id === id) { audience = AUDIENCES[i]; break; }
    }
    if (!audience || audience.id === currentAudience) return;
    currentAudience = audience.id;

    press('data-audience', audience.id);
    setText('a-copy', audience.reading);
    setAttr('a-more', 'href', audience.url);
    // `name` is a sentence — "You have to answer for it" — which reads as a door
    // and not as a noun. Splicing it into another sentence produced "Everything
    // written for you have to answer for it". `label` is the noun.
    setText('a-more-label', 'Everything written for ' + audience.label + ' →');

    if (updateUrl !== false) setUrlParam('audience', audience.id);
  }

  /* -------------------------------------------------------- media switcher -- */

  function selectMedia(name) {
    press('data-media', name);
    var panels = document.querySelectorAll('[data-media-panel]');
    for (var i = 0; i < panels.length; i++) {
      panels[i].hidden = panels[i].getAttribute('data-media-panel') !== name;
    }
  }

  /* ------------------------------------------------------------ wiring up -- */

  // One listener for the document. Every switch is a button carrying the
  // attribute that names its group, so adding a fourth switch is markup rather
  // than JavaScript.
  document.addEventListener('click', function (event) {
    var button = event.target.closest && event.target.closest('button');
    if (!button) return;
    if (button.hasAttribute('data-level'))    return selectLevel(button.getAttribute('data-level'));
    if (button.hasAttribute('data-audience')) return selectAudience(button.getAttribute('data-audience'));
    if (button.hasAttribute('data-media'))    return selectMedia(button.getAttribute('data-media'));
  });

  // Open on whatever the URL asked for, falling back to what the server already
  // rendered. The page is correct before this file runs — every switch only ever
  // changes a page that already said something true.
  var params = new URLSearchParams(location.search);
  var wantLevel = params.get('level');
  var wantAudience = params.get('audience');

  if (byId('p-name')) {
    if (currentPolicy) {
      setText('p-policy', currentPolicy.title);
      setText('p-policy-code', currentPolicy.slug + '/');
      var pu = byId('p-policy-url');
      if (pu) {
        if (currentPolicy.url) { pu.href = currentPolicy.url; }
        else { pu.hidden = true; }
      }
      var dflt = byId('p-policy-default');
      if (dflt) dflt.hidden = currentPolicy.slug !== MODEL.default_policy;
      // whatever was asked for, the address ends up saying what the page is
      // actually selling — a slug the build does not know is not left sitting
      // there looking as though it was honoured
      var asked = new URLSearchParams(location.search).get('policy');
      if (asked && asked !== currentPolicy.slug) setUrlParam('policy', currentPolicy.slug);
    }
    selectLevel(wantLevel && LEVELS.some(function (l) { return l.id === wantLevel; })
      ? wantLevel
      : (MODEL.default_level || (LEVELS[0] && LEVELS[0].id)), false);
  }
  if (byId('a-copy')) {
    selectAudience(wantAudience && AUDIENCES.some(function (a) { return a.id === wantAudience; })
      ? wantAudience
      : (MODEL.default_audience || (AUDIENCES[0] && AUDIENCES[0].id)), false);
  }
  if (document.querySelector('[data-media]')) selectMedia('art');
}());

/* ============================================================================
 * THE JOURNEY — the order, the picker, the hand-off.
 *
 * Added for the v4 pack, which supplied the cart, checkout, post-purchase and
 * policy-picker screens.
 *
 * IT SHARES THE LIVE STORE'S ORDER. The current store's shop.js already keeps an
 * order in this browser under `sgit.store.order.v1`, keyed `slug|level` with a
 * quantity, and generates the reference. This reads and writes THE SAME record
 * in THE SAME shape, so a buyer who starts an order on the store that sells
 * today and wanders into /next/ still has it, and the reverse. Two carts under
 * two keys would be a bug that only shows up for the one person who does both.
 *
 * WHY NOT JUST LOAD shop.js. Because it renders its own markup into #cart, #pay
 * and #order — the current design's markup. Sharing the STATE is the part worth
 * sharing; the rendering is the part being replaced.
 *
 * STILL NO FORMS. Quantities are buttons, the search is a dialog driven by the
 * keyboard, the behaviour filter is a <details>. There is no input, textarea or
 * select anywhere in this site's output and a check holds that line.
 * ========================================================================== */
(function () {
  'use strict';

  var MODEL = (function () {
    var el = document.getElementById('next-model');
    if (!el) return null;
    try { return JSON.parse(el.textContent); } catch (e) { return null; }
  }());
  if (!MODEL || !MODEL.order) return;

  var O = MODEL.order;                      // {schema, key, order_prefix, sku_prefix}
  var LEVELS = {};
  (MODEL.levels || []).forEach(function (l) { LEVELS[l.cart_id] = l; });
  var SHAPES = {};
  (MODEL.shapes || []).forEach(function (s) { SHAPES[s.slug] = s; });

  /* ------------------------------------------------------------------ state */
  var S = { items: {}, ref: null };

  function load() {
    try {
      var got = JSON.parse(window.localStorage.getItem(O.key) || 'null');
      if (!got || got.schema !== O.schema) return;
      S.items = got.items || {};
      S.ref = got.ref || null;
    } catch (e) { /* private window, blocked storage */ }
  }

  function save() {
    try {
      window.localStorage.setItem(O.key, JSON.stringify({
        schema: O.schema, items: S.items, ref: S.ref,
        // shop.js reads these two on pages that carry no model, for its badge.
        // Writing them keeps the live store's header correct after a change made
        // over here, which is the whole point of sharing one record.
        n: count(), label: money(dueTotal())
      }));
    } catch (e) { /* see load() */ }
  }

  /* Six characters, no 0/O or 1/I, so a reference survives being read down a
     phone. Identical alphabet and prefix to shop.js: the same order must produce
     the same shape of reference whichever page created it. */
  function newRef() {
    var a = '23456789ABCDEFGHJKLMNPQRSTUVWXYZ', out = '';
    var r = new Uint32Array(6);
    (window.crypto || window.msCrypto).getRandomValues(r);
    for (var i = 0; i < 6; i++) out += a[r[i] % a.length];
    return O.order_prefix + '-' + out;
  }

  function ref() {
    if (!S.ref) { S.ref = newRef(); save(); }
    return S.ref;
  }

  function money(pence) {
    return '£' + (pence / 100).toLocaleString('en-GB',
      { minimumFractionDigits: pence % 100 ? 2 : 0,
        maximumFractionDigits: pence % 100 ? 2 : 0 });
  }

  /* ------------------------------------------------------------------ codes */
  /* A CODE IS NEVER TYPED. There is no text field on this domain and the gate
     refuses one, so a code arrives in the address — ?code=... or #code=... —
     which is what a printed card or a QR at a stand hands somebody anyway. What
     ships is sha256 of the code; the browser hashes what it was handed and
     compares. What is kept afterwards is the RECORD'S id, never the code, so
     nothing in this browser's storage carries one either.
   *
   * THE HASH BELOW IS A SECOND COPY OF THE ONE IN shop.js, DELIBERATELY, AND A
   * BUILD CHECK HOLDS THE TWO IDENTICAL. Both engines have to agree on what a
   * code hashes to or a card printed today stops working on one half of the
   * site. crypto.subtle would avoid the duplication and is async and absent from
   * a non-secure context, and this site is built to work from a local directory
   * too. One algorithm in two files, pinned, beats one algorithm that is
   * sometimes there.
   *
   * THIS WHOLE BLOCK IS ON ITS WAY OUT. TM-8 on the board retires the
   * browser-side arithmetic the day the codes exist as promotion codes at the
   * payment provider, which is where a discount belongs. Until then a printed
   * card has to work, and this is what makes it work. */

  function sha256(str) {
    var K = [
      0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1,
      0x923f82a4, 0xab1c5ed5, 0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
      0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786,
      0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
      0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147,
      0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
      0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b,
      0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
      0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a,
      0x5b9cca4f, 0x682e6ff3, 0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
      0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2];
    var H = [0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
             0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19];

    /* utf-8, three bytes at most: a code is letters and digits, and the build
       refuses one that is not, so a surrogate pair cannot reach here. */
    var b = [], i, c;
    for (i = 0; i < str.length; i++) {
      c = str.charCodeAt(i);
      if (c < 0x80) { b.push(c); }
      else if (c < 0x800) { b.push(0xc0 | (c >> 6), 0x80 | (c & 63)); }
      else { b.push(0xe0 | (c >> 12), 0x80 | ((c >> 6) & 63), 0x80 | (c & 63)); }
    }
    var bits = b.length * 8;
    b.push(0x80);
    while (b.length % 64 !== 56) b.push(0);
    b.push(0, 0, 0, 0,
           (bits >>> 24) & 255, (bits >>> 16) & 255, (bits >>> 8) & 255, bits & 255);

    function rr(x, n) { return (x >>> n) | (x << (32 - n)); }
    var w = new Array(64);
    for (var off = 0; off < b.length; off += 64) {
      for (i = 0; i < 16; i++) {
        w[i] = (b[off + i * 4] << 24) | (b[off + i * 4 + 1] << 16) |
               (b[off + i * 4 + 2] << 8) | b[off + i * 4 + 3];
      }
      for (i = 16; i < 64; i++) {
        var s0 = rr(w[i - 15], 7) ^ rr(w[i - 15], 18) ^ (w[i - 15] >>> 3);
        var s1 = rr(w[i - 2], 17) ^ rr(w[i - 2], 19) ^ (w[i - 2] >>> 10);
        w[i] = (w[i - 16] + s0 + w[i - 7] + s1) | 0;
      }
      var a = H[0], bb = H[1], cc = H[2], d = H[3],
          e = H[4], f = H[5], g = H[6], h = H[7];
      for (i = 0; i < 64; i++) {
        var S1 = rr(e, 6) ^ rr(e, 11) ^ rr(e, 25);
        var ch = (e & f) ^ (~e & g);
        var t1 = (h + S1 + ch + K[i] + w[i]) | 0;
        var S0 = rr(a, 2) ^ rr(a, 13) ^ rr(a, 22);
        var mj = (a & bb) ^ (a & cc) ^ (bb & cc);
        var t2 = (S0 + mj) | 0;
        h = g; g = f; f = e; e = (d + t1) | 0;
        d = cc; cc = bb; bb = a; a = (t1 + t2) | 0;
      }
      H[0] = (H[0] + a) | 0; H[1] = (H[1] + bb) | 0;
      H[2] = (H[2] + cc) | 0; H[3] = (H[3] + d) | 0;
      H[4] = (H[4] + e) | 0; H[5] = (H[5] + f) | 0;
      H[6] = (H[6] + g) | 0; H[7] = (H[7] + h) | 0;
    }
    return H.map(function (x) { return ('00000000' + (x >>> 0).toString(16)).slice(-8); }).join('');
  }

  function ymd(d) {
    function two(n) { return (n < 10 ? '0' : '') + n; }
    return d.getFullYear() + '-' + two(d.getMonth() + 1) + '-' + two(d.getDate());
  }

  var CODES = {};
  (MODEL.codes || []).forEach(function (c) { CODES[c.id] = c; });
  var CKEY = MODEL.code_storage || 'sgit.store.code.v1';
  var CODE_NOTE = null;

  function held() {
    var id;
    try { id = window.localStorage.getItem(CKEY); } catch (e) { return null; }
    if (!id) return null;
    var c = CODES[id];
    if (!c) return { rec: null, ok: false, why: 'That code is not on the store any more.' };
    if (ymd(new Date()) > c.until) {
      return { rec: c, ok: false, why: 'That code ran out on ' + c.until + '.' };
    }
    return { rec: c, ok: true, why: '' };
  }

  function discount() { var h = held(); return h && h.ok ? h.rec : null; }

  function dropCode() {
    try { window.localStorage.removeItem(CKEY); } catch (e) { /* as above */ }
    CODE_NOTE = null;
    render();
  }

  /* Recognise what was in the address, keep the id, and take the code back out of
     the address bar — a screenshot of an order should not carry one, and a code
     that was NOT recognised should not sit there looking as though it was. */
  function takeCodeFromAddress() {
    var m = /[?&#]code=([A-Za-z0-9]{1,32})/.exec(
      window.location.search + ' ' + window.location.hash);
    if (!m) return;
    var h = sha256(m[1].toUpperCase()), hit = null;
    (MODEL.codes || []).forEach(function (c) { if (c.hash === h) hit = c; });
    if (!hit) {
      CODE_NOTE = { ok: false, text: 'That code is not one of ours. Nothing has changed.' };
    } else if (ymd(new Date()) > hit.until) {
      CODE_NOTE = { ok: false, text: hit.label + ' ran out on ' + hit.until + '.' };
    } else {
      try { window.localStorage.setItem(CKEY, hit.id); } catch (e) { /* as above */ }
      CODE_NOTE = { ok: true, text: hit.pct + '% off, applied to your order.' };
    }
    if (window.history && window.history.replaceState) {
      var q = window.location.search.replace(/^\?/, '').split('&').filter(function (kv) {
        return kv && kv.slice(0, 5).toLowerCase() !== 'code=';
      }).join('&');
      var hash = /^#code=/i.test(window.location.hash) ? '' : window.location.hash;
      window.history.replaceState(null, '',
        window.location.pathname + (q ? '?' + q : '') + hash);
    }
  }

  function pctFor(level) {
    var d = discount();
    if (!d) return 0;
    if (d.levels !== 'all' && d.levels.indexOf(level) < 0) return 0;
    return d.pct;
  }

  /* What a line costs after the code. The deposit split is then taken on what is
     left and never moves, which is the same order shop.js applies them in. */
  function unitOf(lvl) {
    var pct = pctFor(lvl.cart_id);
    return pct ? Math.round(lvl.pence * (100 - pct) / 100) : lvl.pence;
  }

  /* ------------------------------------------------------------------ lines */
  function lines() {
    return Object.keys(S.items).filter(function (k) {
      // A level or a shape can be renamed between releases and an order is local
      // storage that outlives one. A key naming something this build does not
      // have is dropped rather than rendered: the alternative is an order page
      // that throws and a reader who cannot even empty it.
      var p = k.split('|');
      return LEVELS[p[1]] && SHAPES[p[0]] && S.items[k] > 0;
    }).map(function (k) {
      var p = k.split('|'), lvl = LEVELS[p[1]], qty = S.items[k];
      var unit = unitOf(lvl);
      var now = Math.round(unit * lvl.pay_now_pct / 100) * qty;
      return { key: k, slug: p[0], level: p[1], qty: qty,
               shape: SHAPES[p[0]], lvl: lvl,
               sku: O.sku_prefix + '-' + SHAPES[p[0]].code + '-' + lvl.cart_code,
               unit: unit, list: lvl.pence,
               off: (lvl.pence - unit) * qty,
               sum: unit * qty, now: now, later: unit * qty - now };
    }).sort(function (a, b) {
      return a.lvl.n.localeCompare(b.lvl.n) || a.slug.localeCompare(b.slug);
    });
  }

  function count()    { return lines().reduce(function (t, l) { return t + l.qty; }, 0); }
  function dueTotal() { return lines().reduce(function (t, l) { return t + l.sum; }, 0); }
  function dueNow()   { return lines().reduce(function (t, l) { return t + l.now; }, 0); }
  function dueLater() { return lines().reduce(function (t, l) { return t + l.later; }, 0); }

  function change(slug, level, by) {
    var k = slug + '|' + level;
    var n = (S.items[k] || 0) + by;
    if (n <= 0) { delete S.items[k]; } else { S.items[k] = Math.min(n, 99); }
    if (!Object.keys(S.items).length) S.ref = null;
    save();
    render();
  }

  /* ----------------------------------------------------------------- render */
  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }

  function badge() {
    var n = count();
    Array.prototype.forEach.call(document.querySelectorAll('[data-order-count]'),
      function (e) { e.textContent = n ? ' (' + n + ')' : ''; });
  }

  function renderLine(l) {
    var row = el('div', 'n-line');
    row.appendChild(el('div', 'n-line__glyph', 'ABP'));

    var mid = el('div');
    mid.appendChild(el('h3', null, l.shape.title));
    mid.appendChild(el('p', 'n-line__lvl', 'ABP ' + l.lvl.short_name +
      (l.qty > 1 ? ' × ' + l.qty : '')));
    mid.appendChild(el('p', 'n-line__clock', l.lvl.clock_full));

    var claim = el('a', 'n-claim n-claim--' + l.lvl.state,
      l.lvl.state_label + ' ↗');
    claim.href = (MODEL.ledger_url || '/ledger/') + '#claim-' + l.lvl.claim;
    claim.style.marginTop = '10px';
    mid.appendChild(claim);

    var acts = el('div', 'n-line__acts');
    [['Remove', -l.qty], ['−', -1], ['+', 1]].forEach(function (pair) {
      var b = el('button', null, pair[0]);
      b.type = 'button';
      b.setAttribute('data-change', l.slug + '|' + l.level + '|' + pair[1]);
      b.setAttribute('aria-label', (pair[1] > 0 ? 'Add another ' : 'Remove ') +
        'ABP ' + l.lvl.short_name + ' for ' + l.shape.title);
      acts.appendChild(b);
    });
    mid.appendChild(acts);
    row.appendChild(mid);

    var money$ = el('div', 'n-line__money');
    money$.appendChild(el('b', null, money(l.sum)));
    if (l.off) {
      var was = el('span', 'n-line__was', money(l.list * l.qty));
      money$.appendChild(was);
    }
    if (l.later) {
      money$.appendChild(el('span', null, money(l.now) + ' now'));
      money$.appendChild(el('span', null, money(l.later) + ' on delivery'));
    } else {
      money$.appendChild(el('span', null, 'in full, on the order'));
    }
    row.appendChild(money$);
    return row;
  }

  /* What the reader is holding, where they can see it and drop it. A discount
     that only shows up in the arithmetic is a discount nobody can check. */
  function renderCodeBar(host) {
    var h = held();
    if (!h && !CODE_NOTE) return;
    var bar = el('div', 'n-code' + ((h && h.ok) || (CODE_NOTE && CODE_NOTE.ok)
      ? ' n-code--on' : ' n-code--off'));
    var said = el('div');
    if (h && h.ok) {
      said.appendChild(el('b', null, h.rec.label));
      said.appendChild(el('span', null, h.rec.pct + '% off'
        + (h.rec.levels === 'all' ? ' every level' : ' some levels')
        + ', until ' + h.rec.until + '.'));
    } else if (h) {
      said.appendChild(el('b', null, 'No discount is held'));
      said.appendChild(el('span', null, h.why));
    } else {
      said.appendChild(el('b', null, CODE_NOTE.ok ? 'Code applied' : 'Code not applied'));
      said.appendChild(el('span', null, CODE_NOTE.text));
    }
    bar.appendChild(said);
    if (h) {
      var drop = el('button', null, 'Remove it');
      drop.type = 'button';
      drop.addEventListener('click', dropCode);
      bar.appendChild(drop);
    }
    host.appendChild(bar);
  }

  function renderOrder(host) {
    var ls = lines();
    host.replaceChildren();

    if (!ls.length) {
      var empty = el('div', 'n-empty');
      empty.appendChild(el('h2', null, 'Your order is empty'));
      empty.appendChild(el('p', null,
        'Choose a policy shape and the level you want it at.'));
      var a = el('a', 'n-btn', 'Pick an agent →');
      a.href = MODEL.picker_url || '/next/policies/';
      empty.appendChild(a);
      host.appendChild(empty);
      badge();
      return;
    }

    ls.forEach(function (l) { host.appendChild(renderLine(l)); });

    var totals = el('div', 'n-totals');
    function row(label, value, cls) {
      var d = el('div', cls || null);
      d.appendChild(el('span', null, label));
      d.appendChild(el('b', null, value));
      return d;
    }
    var off = ls.reduce(function (s, l) { return s + l.off; }, 0);
    if (off) totals.appendChild(row('Taken off by your code', '\u2212' + money(off)));
    totals.appendChild(row('Due now', money(dueNow())));
    if (dueLater()) totals.appendChild(row('Due on delivery', money(dueLater())));
    totals.appendChild(row('Total', money(dueTotal()), 'is-total'));
    host.appendChild(totals);

    var foot = el('div', 'n-mt');
    foot.style.display = 'flex';
    foot.style.gap = '14px';
    foot.style.flexWrap = 'wrap';
    foot.style.alignItems = 'center';
    var go = el('a', 'n-btn', 'Continue to checkout →');
    go.href = MODEL.checkout_url || '/next/checkout/';
    foot.appendChild(go);
    var r = el('span', 'n-ref');
    r.appendChild(el('span', null, ref()));
    foot.appendChild(r);
    host.appendChild(foot);
    badge();
  }

  function renderCheckout(host) {
    var ls = lines();
    host.replaceChildren();
    if (!ls.length) {
      var empty = el('div', 'n-empty');
      empty.appendChild(el('h2', null, 'Nothing to check out'));
      var a = el('a', 'n-btn', 'Pick an agent →');
      a.href = MODEL.picker_url || '/next/policies/';
      empty.appendChild(a);
      host.appendChild(empty);
      badge();
      return;
    }
    var totals = el('div', 'n-totals');
    function row(label, value, cls) {
      var d = el('div', cls || null);
      d.appendChild(el('span', null, label));
      d.appendChild(el('b', null, value));
      return d;
    }
    totals.appendChild(row('Due now, at the provider', money(dueNow())));
    if (dueLater()) {
      totals.appendChild(row('Due when the work is in your hands', money(dueLater())));
    }
    totals.appendChild(row('Your order reference', ref(), 'is-total'));
    host.appendChild(totals);

    var note = el('p', 'n-note n-note--hold n-mt');
    note.innerHTML = '<b>The payment link has not been issued yet.</b> When it is, ' +
      'this button opens the provider’s own page, which is where a card is typed. ' +
      'The amount and the reference are all that reach it.';
    host.appendChild(note);

    /* NOT FULL WIDTH. A pale, full-width, left-aligned bordered box on a page
       whose whole argument is that this site has no fields reads as a field.
       Sized to its own text it reads as what it is: a button that is off. */
    var btn = el('button', 'n-btn n-mt',
      'The payment link has not been issued yet');
    btn.type = 'button';
    btn.setAttribute('aria-disabled', 'true');
    host.appendChild(btn);
    badge();
  }

  /* ---------------------------------------------------------------- receipt */
  /* The post-purchase page. NOTHING HAS BEEN PAID FOR: no payment link has been
     issued on any level, so this page can only ever show the order this browser
     is holding, and it says so rather than dressing an example as a purchase. */
  function renderReceipt(host) {
    var ls = lines();
    host.replaceChildren();

    if (!ls.length) {
      var empty = el('div', 'n-empty');
      empty.appendChild(el('h2', null, 'This browser is not holding an order'));
      empty.appendChild(el('p', null,
        'Nothing has been bought here — no payment link has been issued on any level. '
        + 'Build an order and it appears on this page, reference and all, the way it '
        + 'will when a link exists.'));
      var a = el('a', 'n-btn', 'Pick an agent →');
      a.href = MODEL.picker_url || '/next/policies/';
      empty.appendChild(a);
      host.appendChild(empty);
      badge();
      return;
    }

    ls.forEach(function (l) {
      var card = el('div', 'n-receipt');

      var left = el('div');
      left.appendChild(el('p', 'n-receipt__label', 'WHAT YOU CHOSE'));
      left.appendChild(el('h2', null, 'ABP ' + l.lvl.short_name));
      left.appendChild(el('p', null, l.shape.title));
      var sku = el('p', 'n-fine');
      sku.appendChild(el('code', null, l.sku + (l.qty > 1 ? ' × ' + l.qty : '')));
      left.appendChild(sku);
      var claim = el('a', 'n-claim n-claim--' + l.lvl.state,
        l.lvl.state_label + ' ↗');
      claim.href = (MODEL.ledger_url || '/ledger/') + '#claim-' + l.lvl.claim;
      left.appendChild(claim);

      var right = el('div');
      right.appendChild(el('p', 'n-receipt__label', 'WHAT IT COSTS'));
      right.appendChild(el('h2', null, money(l.sum)));
      right.appendChild(el('p', null, l.later
        ? money(l.now) + ' now · ' + money(l.later) + ' on delivery'
        : 'in full, on the order'));
      right.appendChild(el('p', 'n-fine', l.lvl.clock_full));

      card.appendChild(left);
      card.appendChild(right);
      host.appendChild(card);
    });

    var foot = el('div', 'n-mt');
    var r = el('span', 'n-ref');
    r.appendChild(el('span', null, ref()));
    var copy = el('button', null, 'copy');
    copy.type = 'button';
    copy.setAttribute('data-copy-ref', '');
    r.appendChild(copy);
    foot.appendChild(r);
    host.appendChild(foot);

    var says = el('p', 'n-fine n-dim n-mt');
    says.textContent = 'This reference is in this browser and nowhere else. It has never '
      + 'been sent anywhere, because there is nowhere to send it to yet.';
    host.appendChild(says);
    badge();
  }

  /* ------------------------------------------------------------------ steps */
  /* The "what happens next" panels on the post-purchase page: one per level,
     one shown at a time. Same shape as the media switcher in the first block. */
  function selectStep(id) {
    Array.prototype.forEach.call(document.querySelectorAll('[data-step]'),
      function (b) { b.setAttribute('aria-pressed',
        String(b.getAttribute('data-step') === id)); });
    Array.prototype.forEach.call(document.querySelectorAll('[data-step-panel]'),
      function (pane) { pane.hidden = pane.getAttribute('data-step-panel') !== id; });
  }

  /* ----------------------------------------------------------------- picker */
  function pickerFilter() {
    var q = (document.body.getAttribute('data-q') || '').toLowerCase();
    var fam = document.body.getAttribute('data-family') || 'all';
    var ev = document.body.getAttribute('data-evidence') || 'all';
    var beh = document.body.getAttribute('data-behaviour') || 'all';
    var shown = 0;

    Array.prototype.forEach.call(document.querySelectorAll('[data-policy]'),
      function (card) {
        var s = SHAPES[card.getAttribute('data-policy')] || {};
        // THE BEHAVIOUR FILTER IS NOT IN THIS TERM, AND THAT IS THE HONEST
        // ANSWER. See the note rendered below: the capability vocabulary is
        // promoted and the per-shape counts are promoted, but the join between
        // them — which of the 23 primitives THIS shape was granted — is not
        // published, so there is nothing to filter on. Filtering on a guess
        // would return a confident, wrong answer to the one reader who cares
        // enough to use it.
        var ok = (fam === 'all' || s.family === fam)
              && (ev === 'all' || s.evidence === ev)
              && (!q || (s.search || '').indexOf(q) !== -1);
        card.hidden = !ok;
        if (ok) shown++;
      });

    // A group whose every card is hidden hides with them, so the page never
    // shows a heading with nothing under it.
    Array.prototype.forEach.call(document.querySelectorAll('[data-group]'),
      function (g) {
        var any = g.querySelectorAll('[data-policy]:not([hidden])').length;
        g.hidden = !any;
        var n = g.querySelector('[data-group-count]');
        if (n) n.textContent = '· ' + any;
      });

    var c = document.getElementById('picker-count');
    if (c) {
      c.textContent = shown + (shown === 1 ? ' policy shape' : ' policy shapes')
        + (shown ? '' : ' — nothing matches those filters')
        + (q ? ' matching “' + q + '”' : '');
    }

    var note = document.getElementById('picker-behaviour-note');
    if (note) {
      note.hidden = beh === 'all';
      var name = document.getElementById('picker-behaviour-name');
      if (name) name.textContent = beh;
    }
  }

  /* ----------------------------------------------------------------- search */
  /* SEARCH WITHOUT A FIELD. This site has no <input>, <select> or <form> in its
     output anywhere, and that rule is not moving for a filter box. So the query
     is held on the body as data-q, typed characters are read off the document,
     and what the reader sees is the query echoed in a dialog — there is no
     element to type into, because there is no element at all.
   *
   * The cost is real and is stated on the page rather than hidden: a phone with
   * no hardware keyboard cannot type here. The handback drew an on-screen
   * keyboard out of buttons to solve that; twenty-six buttons to filter fifteen
   * items is worse than the fifteen items, so on a touch device the category and
   * evidence chips are the filter and the dialog says so. */
  var searchOpen = false;

  function setQuery(q) {
    document.body.setAttribute('data-q', q);
    var echo = document.getElementById('search-q');
    if (echo) {
      echo.textContent = q || '';
      echo.setAttribute('data-empty', String(!q));
    }
    pickerFilter();
  }

  function openSearch() {
    var box = document.getElementById('search');
    if (!box) return;
    searchOpen = true;
    box.hidden = false;
    var chip = document.querySelector('[data-search-open]');
    if (chip) chip.setAttribute('aria-expanded', 'true');
  }

  function closeSearch() {
    var box = document.getElementById('search');
    if (!box) return;
    searchOpen = false;
    box.hidden = true;
    var chip = document.querySelector('[data-search-open]');
    if (chip) chip.setAttribute('aria-expanded', 'false');
  }

  function onKey(event) {
    if (!document.getElementById('search')) return;
    var k = event.key;
    if (!searchOpen) {
      if (k === '/') { event.preventDefault(); openSearch(); }
      return;
    }
    var q = document.body.getAttribute('data-q') || '';
    if (k === 'Escape') { event.preventDefault(); setQuery(''); return closeSearch(); }
    if (k === 'Enter')  { event.preventDefault(); return closeSearch(); }
    if (k === 'Backspace') { event.preventDefault(); return setQuery(q.slice(0, -1)); }
    if (k.length === 1 && !event.metaKey && !event.ctrlKey && !event.altKey) {
      event.preventDefault();
      return setQuery((q + k.toLowerCase()).slice(0, 40));
    }
  }

  function setFilter(kind, value) {
    document.body.setAttribute('data-' + kind, value);
    Array.prototype.forEach.call(
      document.querySelectorAll('[data-filter="' + kind + '"]'), function (b) {
        b.setAttribute('aria-pressed', String(b.getAttribute('data-value') === value));
      });
    pickerFilter();
  }

  function selectPolicy(slug) {
    var s = SHAPES[slug];
    if (!s) return;
    Array.prototype.forEach.call(document.querySelectorAll('[data-policy]'),
      function (b) { b.setAttribute('aria-pressed',
        String(b.getAttribute('data-policy') === slug)); });

    var host = document.getElementById('panel');
    if (!host) return;
    host.setAttribute('data-slug', slug);

    var set = function (id, v) { var e = document.getElementById(id);
                                 if (e) e.textContent = v; };
    set('panel-title', s.title);
    set('panel-slug', s.slug + '/');
    set('panel-summary', s.summary);
    set('panel-can', s.can);
    set('panel-wanted', s.wanted);
    set('panel-unasked', s.unasked);
    set('panel-unbounded', s.unbounded);

    var chip = document.getElementById('panel-claim');
    if (chip) {
      chip.textContent = s.evidence_label + ' ↗';
      chip.className = 'n-claim n-claim--' + s.evidence_state;
    }

    // the example vault and the policy itself are on the shape's own published
    // page upstream; a shape with no page (the catch-all) shows no link rather
    // than a dead one
    var open = document.getElementById('panel-open');
    if (open) {
      if (s.url) { open.href = s.url; open.hidden = false; }
      else { open.hidden = true; }
    }

    /* ONE CELL PER CAPABILITY, AND NOT ONE OF THEM IS COLOURED.
       The first version of this painted the first `wanted` cells green and the
       last `unbounded` cells amber, which looks like a decomposition of the
       grant and is not one: for five of the fifteen shapes, wanted and not-asked
       do not sum to the grant at all, so the colours were drawing a partition
       the data does not contain. Upstream publishes four totals, not a per-cell
       classification. The strip shows the size of the grant, which is what the
       four totals actually support, and the caption says the rest. */
    var cells = document.getElementById('panel-cells');
    if (cells) {
      cells.replaceChildren();
      for (var i = 0; i < s.can; i++) cells.appendChild(document.createElement('i'));
    }

    var sums = document.getElementById('panel-sums');
    if (sums) {
      sums.hidden = !s.sum_note;
      sums.textContent = s.sum_note || '';
    }

    Array.prototype.forEach.call(document.querySelectorAll('[data-add]'),
      function (b) { b.disabled = false; });
    var e = document.getElementById('panel-empty');
    if (e) e.hidden = true;
    var b = document.getElementById('panel-body');
    if (b) b.hidden = false;
  }

  /* -------------------------------------------------------------- listeners */
  document.addEventListener('click', function (event) {
    var t = event.target.closest && event.target.closest('button, a');
    if (!t) return;

    if (t.hasAttribute('data-change')) {
      var p = t.getAttribute('data-change').split('|');
      return change(p[0], p[1], parseInt(p[2], 10));
    }
    if (t.hasAttribute('data-policy')) {
      return selectPolicy(t.getAttribute('data-policy'));
    }
    if (t.hasAttribute('data-filter')) {
      return setFilter(t.getAttribute('data-filter'), t.getAttribute('data-value'));
    }
    if (t.hasAttribute('data-step')) {
      return selectStep(t.getAttribute('data-step'));
    }
    if (t.hasAttribute('data-search-open')) {
      return openSearch();
    }
    if (t.hasAttribute('data-add-line')) {
      // the product page: one policy at one level, straight onto the order
      var line = t.getAttribute('data-add-line').split('|');
      if (!SHAPES[line[0]] || !LEVELS[line[1]]) return;
      change(line[0], line[1], 1);
      var told = document.getElementById('p-added');
      if (told) told.hidden = false;
      return;
    }
    if (t.hasAttribute('data-add')) {
      var host = document.getElementById('panel');
      var slug = host && host.getAttribute('data-slug');
      if (!slug) return;
      change(slug, t.getAttribute('data-add'), 1);
      var go = document.getElementById('panel-added');
      if (go) { go.hidden = false; }
      return;
    }
    if (t.hasAttribute('data-print')) {
      // the receipt prints as a receipt: the print stylesheet drops the chrome,
      // the filters and the button that did the printing
      window.print();
      return;
    }
    if (t.hasAttribute('data-copy-ref')) {
      var r = ref();
      if (navigator.clipboard) navigator.clipboard.writeText(r).catch(function () {});
      t.textContent = 'copied';
      window.setTimeout(function () { t.textContent = 'copy'; }, 1400);
      return;
    }
  });

  function render() {
    // The slot is in the chrome, so a code is acknowledged on whatever page it
    // landed on. A printed card points at the front page; before this, a code
    // that was not ours changed nothing and said nothing, which reads exactly
    // like a code that worked.
    Array.prototype.forEach.call(document.querySelectorAll('[data-code-bar]'),
      function (slot) { slot.replaceChildren(); renderCodeBar(slot); });
    var o = document.getElementById('order');
    if (o) renderOrder(o);
    var c = document.getElementById('checkout');
    if (c) renderCheckout(c);
    var r = document.getElementById('receipt');
    if (r) renderReceipt(r);
    badge();
  }

  load();
  takeCodeFromAddress();
  render();
  document.addEventListener('keydown', onKey);
  if (document.querySelector('[data-step]')) {
    var firstStep = document.querySelector('[data-step]');
    selectStep(firstStep.getAttribute('data-step'));
  }
  if (document.querySelector('[data-policy]')) {
    pickerFilter();
    var first = new URLSearchParams(location.search).get('policy');
    if (first && SHAPES[first]) selectPolicy(first);
  }
}());
