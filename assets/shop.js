/* shop.js — the store: the catalogue, a shape's four levels, and the cart.
 *
 * NOTHING HERE OPENS A CONNECTION AND NOTHING HERE IS A FORM. Every control is a
 * button, because this site collects nothing from anybody and a build check holds
 * the whole of docs/ to no form, no input, no textarea, no select. The cart lives
 * in local storage; the name, the contact and the card are taken by the payment
 * provider on its own pages, which is the only place a card number should be
 * typed. What reaches the provider is an amount and an order reference, and the
 * reference carries the SKUs.
 *
 * FILTERING WITHOUT A SEARCH BOX. Fifteen shapes is small enough that chips beat
 * a text field, which is lucky, because a text field is a form control this
 * site does not have and a build check will not let it have. The chips
 * filter by family and by what is in the way; the sort is three buttons.
 */
(function () {
  'use strict';

  var KEY_ONLY = 'sgit.store.order.v1';

  /* The nav carries an order badge on EVERY page, and only three pages carry the
     model. So the cart writes its own count and total into storage beside the
     items, and a page without a model renders the badge from that and stops. The
     alternative — shipping the whole catalogue to every page for a number in the
     corner — is a worse trade. */
  var modelEl = document.getElementById('shop-model');
  if (!modelEl) {
    /* A discount code arrives in the address, off a printed card or a QR. If it
       lands on a page that carries no catalogue there is nothing here to check
       it against, so it is carried to the one that does rather than dropped. */
    var stray = /[?&#]code=([A-Za-z0-9]{1,32})/.exec(
      window.location.search + ' ' + window.location.hash);
    if (stray) {
      /* THE STORE'S OWN ORDER PAGE, NOT THE PICKER. Until v0.3.16 this went to
         /policies/, which carried the catalogue and so could check a code. That
         page is the new design's picker now and this engine is not on it; the
         cart is where the new engine reads a code, and it is also the page a
         reader who followed a discount actually wants. */
      window.location.replace('/cart/index.html?code=' + stray[1]);
      return;
    }
    try {
      var got = JSON.parse(window.localStorage.getItem(KEY_ONLY) || 'null');
      paintBadge(got && got.n, got && got.label);
    } catch (e) { /* private window, blocked storage */ }
    return;
  }
  var M = JSON.parse(modelEl.textContent);
  var KEY = M.storage;
  var LEVELS = {};
  M.levels.forEach(function (l) { LEVELS[l.id] = l; });
  var SHAPES = {};
  M.shapes.forEach(function (s) { SHAPES[s.slug] = s; });
  var CODES = {};
  (M.codes || []).forEach(function (c) { CODES[c.id] = c; });
  var CKEY = M.code_storage;
  var CODE_NOTE = null;     // what to say about a code that just arrived

  /* ------------------------------------------------------------- sha256 ----
     Here because the page has to RECOGNISE a discount code without CARRYING
     one. What ships in the model is sha256 of the upper-cased code; the browser
     hashes what it was handed and compares. crypto.subtle would do the same,
     but only in a secure context and only as a promise — and this site is built
     to work from a local directory as well as over https, so it is done here
     and every renderer stays synchronous.

     data/discounts.yml says what a hash is and is not worth: a nine-character
     code can be ground out of one, and the thing that stops a stranger paying
     nothing is not this function — it is that a browser does not take money. */
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

  /* --------------------------------------------------------- the code ----
     A code is never typed: no page on this site has a text field and the gate
     refuses one. It arrives in the address — ?code=... or #code=... — which is
     what a card at a stand hands somebody anyway. What is kept afterwards is the
     RECORD'S ID, not the code, so nothing in this browser's storage carries one
     either. It comes off the price of every line it applies to; the deposit
     split is then taken on what is left, and never moves. */

  function ymd(d) {
    function two(n) { return (n < 10 ? '0' : '') + n; }
    return d.getFullYear() + '-' + two(d.getMonth() + 1) + '-' + two(d.getDate());
  }

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

  /* Recognise what was in the address, keep the id, and take the code back out
     of the address bar — a screenshot of a checkout should not carry one, and a
     code that was NOT recognised should not sit there looking as though it was. */
  function takeCodeFromAddress() {
    var m = /[?&#]code=([A-Za-z0-9]{1,32})/.exec(
      window.location.search + ' ' + window.location.hash);
    if (!m) return;
    var h = sha256(m[1].toUpperCase()), hit = null;
    (M.codes || []).forEach(function (c) { if (c.hash === h) hit = c; });
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

  function unitOf(level) {
    var list = LEVELS[level].price, pct = pctFor(level);
    return pct ? Math.round(list * (100 - pct) / 100) : list;
  }

  function paintBadge(n, label) {
    /* The new chrome's badge. Every page outside /v1/ is served in it, and on a
       page that carries no next-model this engine is the only one that knows the
       count. Same record, two renderers. */
    Array.prototype.forEach.call(document.querySelectorAll('[data-order-count]'), function (e) {
      e.textContent = n ? ' (' + n + ')' : '';
    });
    Array.prototype.forEach.call(document.querySelectorAll('[data-cart-count]'), function (e) {
      e.textContent = n ? String(n) : '';
      e.hidden = !n;
    });
    Array.prototype.forEach.call(document.querySelectorAll('[data-cart-total]'), function (e) {
      e.textContent = n ? (label || '') : '';
    });
  }

  /* ------------------------------------------------------------------ state */
  var S = { items: {}, ref: null, filter: 'all', sort: 'unbounded', rail: null };

  function load() {
    try {
      var raw = window.localStorage.getItem(KEY);
      if (!raw) return;
      var got = JSON.parse(raw);
      if (!got || got.schema !== M.schema) return;
      S.items = got.items || {};
      S.ref = got.ref || null;
    } catch (e) { /* private window, blocked storage, full quota */ }
  }

  function save() {
    try {
      window.localStorage.setItem(KEY, JSON.stringify(
        { schema: M.schema, items: S.items, ref: S.ref,
          // written for the badge on pages that carry no model
          n: count(), label: money(total()) }));
    } catch (e) { /* see load() */ }
  }

  /* An order reference is six characters from an alphabet with no 0/O or 1/I, so
     it survives being read down a phone or typed off a screen. It is not an
     account: it exists in this browser and on whatever the buyer pastes it into. */
  function newRef() {
    var a = '23456789ABCDEFGHJKLMNPQRSTUVWXYZ', out = '';
    var r = new Uint32Array(6);
    (window.crypto || window.msCrypto).getRandomValues(r);
    for (var i = 0; i < 6; i++) out += a[r[i] % a.length];
    return M.order_prefix + '-' + out;
  }

  function ref() {
    if (!S.ref) { S.ref = newRef(); save(); }
    return S.ref;
  }

  /* --------------------------------------------------------------- the cart */
  function sku(slug, level) {
    return M.sku_prefix + '-' + (SHAPES[slug] ? SHAPES[slug].code : '???') +
           '-' + LEVELS[level].code;
  }

  function add(slug, level, by) {
    var k = slug + '|' + level;
    var n = (S.items[k] || 0) + (by === undefined ? 1 : by);
    if (n <= 0) { delete S.items[k]; } else { S.items[k] = Math.min(n, 99); }
    if (!Object.keys(S.items).length) S.ref = null;
    save();
    render();
  }

  function lines() {
    return Object.keys(S.items).filter(function (k) {
      /* A level can be renamed between releases, and a cart is local storage that
         outlives one. A key naming a level this build does not have is dropped
         rather than rendered — the alternative is a cart page that throws and a
         reader who cannot even empty it. */
      var p = k.split('|');
      return LEVELS[p[1]] && S.items[k] > 0;
    }).map(function (k) {
      var p = k.split('|'), slug = p[0], level = p[1];
      var unit = unitOf(level);
      return { slug: slug, level: level, qty: S.items[k],
               shape: SHAPES[slug], lvl: LEVELS[level],
               sku: sku(slug, level), unit: unit, list: LEVELS[level].price,
               off: (LEVELS[level].price - unit) * S.items[k],
               sum: unit * S.items[k] };
    }).sort(function (a, b) { return a.lvl.n - b.lvl.n || a.slug.localeCompare(b.slug); });
  }

  function total() {
    return lines().reduce(function (t, l) { return t + l.sum; }, 0);
  }

  function count() {
    return lines().reduce(function (t, l) { return t + l.qty; }, 0);
  }

  /* What is taken now, and what is owed on delivery. The split is a property of
     the OFFER, not of the rail: a card tapped on a terminal at the stand takes the
     same deposit as a link opened on a phone. Two of the four levels are produced
     without anybody being scheduled and take the whole price; the two that are
     somebody's work take a deposit, because selling an hour of a person from a
     card — for work that has never run for a paying buyer — should not put the
     whole amount on one side of the table before anybody has done anything. */
  function splitOf(line) {
    var pct = line.lvl.pay_now_pct == null ? 100 : line.lvl.pay_now_pct;
    var now = Math.round(line.unit * pct / 100) * line.qty;
    return { now: now, later: line.sum - now, pct: pct };
  }

  function dueNow() {
    return lines().reduce(function (t, l) { return t + splitOf(l).now; }, 0);
  }

  function dueLater() {
    return lines().reduce(function (t, l) { return t + splitOf(l).later; }, 0);
  }

  function listTotal() {
    return lines().reduce(function (t, l) { return t + l.list * l.qty; }, 0);
  }

  function saved() { return listTotal() - total(); }

  /* ---------------------------------------------------------- the wallet ----
     A DEMONSTRATION, and every screen it appears on says so before it says
     anything else. It charges nothing, there is no account, and nothing leaves
     this browser: the balance is local storage on the reader's own machine and it
     goes when they clear site data. It exists so the whole flow — catalogue,
     order, payment, and the page that says what happens now — can be walked
     before a single real payment link has been issued.

     It never blocks either. An empty wallet tops itself back up, because the
     interesting part is the ledger and the post-sale page, not a gate. */
  var WKEY = 'sgit.store.wallet.v1';
  var TOPUP = 200000;   // pence — £2,000, enough to buy anything on the list

  function wallet() {
    try {
      var w = JSON.parse(window.localStorage.getItem(WKEY) || 'null');
      if (w && w.schema === 1) return w;
    } catch (e) { /* private window, blocked storage */ }
    return { schema: 1, balance: TOPUP, spent: 0, topups: 0, orders: [] };
  }

  function saveWallet(w) {
    try { window.localStorage.setItem(WKEY, JSON.stringify(w)); } catch (e) { /* as above */ }
  }

  function money(pence) {
    return '£' + (pence / 100).toLocaleString('en-GB',
      { minimumFractionDigits: pence % 100 ? 2 : 0, maximumFractionDigits: 2 });
  }

  /* The string a payment provider is handed. Order reference first, because that
     is what a human reads back; then one token per line, with a quantity only
     where it is not one. Short on purpose: a reference field is not a database. */
  function orderString() {
    return ref() + ' ' + lines().map(function (l) {
      return l.sku + (l.qty > 1 ? '*' + l.qty : '');
    }).join(' ');
  }

  /* An order is the record the post-sale page renders from. It is written when a
     rail is used and it is never sent anywhere: on the simulated rail nothing
     leaves the browser at all, and on a real rail what reaches the provider is
     still only the amount and the reference. */
  function placeOrder(railId) {
    var w = wallet();
    var now = dueNow();
    if (railId === 'wallet') {
      if (w.balance < now) { w.balance = TOPUP; w.topups += 1; }
      w.balance -= now;
      w.spent += now;
    }
    var d = discount();
    var order = {
      ref: ref(),
      at: new Date().toISOString(),
      rail: railId,
      paid_now: now,
      due_later: dueLater(),
      total: total(),
      list_total: listTotal(),
      /* the code's LABEL and its percentage, never the code */
      code: d ? { id: d.id, pct: d.pct, label: d.label, off: saved() } : null,
      lines: lines().map(function (l) {
        var s = splitOf(l);
        return { sku: l.sku, slug: l.slug, level: l.level, qty: l.qty,
                 title: l.shape ? l.shape.title : l.slug, lvl: l.lvl.name,
                 sum: l.sum, list: l.list * l.qty, off: l.off,
                 now: s.now, later: s.later };
      }),
    };
    w.orders = [order].concat(w.orders || []).slice(0, 25);
    saveWallet(w);
    S.items = {}; S.ref = null; save();
    try { window.localStorage.setItem('sgit.store.lastorder.v1', JSON.stringify(order)); }
    catch (e) { /* the order page falls back to the newest in the wallet */ }
    window.location.href = M.root + 'order/index.html';
  }

  function lastOrder() {
    try {
      var o = JSON.parse(window.localStorage.getItem('sgit.store.lastorder.v1') || 'null');
      if (o && o.ref) return o;
      var w = wallet();
      return (w.orders && w.orders[0]) || null;
    } catch (e) { return null; }
  }

  /* ------------------------------------------------------------------ dom */
  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }

  function btn(cls, text, fn) {
    var b = el('button', cls, text);
    b.type = 'button';
    b.addEventListener('click', fn);
    return b;
  }

  /* The code, said once at the top of whatever page the reader is on. It is a
     chip and a button rather than a field, and it names what came off rather
     than repeating the code — which is not in this browser's storage to repeat. */
  // THE SHOP FRONT'S OWN PRICES, WHEN A CODE IS HELD.
  //
  // The four cards on the home page are built at build time and carry the list
  // price, which is right until somebody follows a link with a code on it. Then
  // the card is the thing they are looking at and the thing that has to change:
  // a person holding a laptop at a stand should not have to say "it did work,
  // look at the bar at the top".
  //
  // The list price stays on screen, struck through. A discount that hides what it
  // came off is a discount nobody can check.
  // THE PAGE A BUYER LANDS ON AFTER PAYING, FILLED IN FROM THIS BROWSER.
  //
  // It is a static page and it is correct with no script at all — somebody whose
  // browser blocked this still reads what happens next, which is the part that
  // matters. What the script adds is the reference, and only if this is the same
  // browser that placed the order. It never invents one: a page that shows a made
  // up reference to somebody who has just paid is worse than a page that says it
  // does not have theirs.
  function renderPaidRef() {
    var box = document.getElementById('paid-order');
    if (!box) return;
    var o = lastOrder();
    if (!o || !o.ref) return;
    box.textContent = '';
    box.appendChild(el('b', null, 'Your order reference'));
    box.appendChild(el('code', 'paid-code', String(o.ref)));
    box.appendChild(el('span', null,
      'It is on your receipt too. Quote it in any message about this order.'));
    box.className = 'paid-ref paid-ref-has';
  }

  function renderSkuPrices() {
    var cards = document.querySelectorAll('.sku[id^="sku-"]');
    if (!cards.length) return;
    for (var i = 0; i < cards.length; i++) {
      var id = cards[i].id.slice(4);
      var lvl = LEVELS[id];
      var box = cards[i].querySelector('.sku-price');
      if (!lvl || !box) continue;
      var b = box.querySelector('b');
      if (!b) continue;
      if (!b.getAttribute('data-list')) b.setAttribute('data-list', b.textContent);
      var was = box.querySelector('.sku-was');
      if (was && was.parentNode) was.parentNode.removeChild(was);
      var pct = pctFor(id);
      if (!pct) { b.textContent = b.getAttribute('data-list'); continue; }
      b.textContent = money(unitOf(id));
      var s = el('span', 'sku-was');
      s.appendChild(el('s', null, b.getAttribute('data-list')));
      s.appendChild(document.createTextNode(' \u00b7 ' + pct + '% off'));
      box.insertBefore(s, box.firstChild.nextSibling);
    }
  }

  function renderCodeBar() {
    var old = document.querySelector('.codebar');
    if (old && old.parentNode) old.parentNode.removeChild(old);
    var h = held();
    if (!h && !CODE_NOTE) return;
    var main = document.querySelector('main');
    if (!main) return;

    var ok = (h && h.ok) || (!h && CODE_NOTE && CODE_NOTE.ok);
    var bar = el('div', 'codebar' + (ok ? '' : ' codebar-off'));
    if (h && h.ok) {
      var chip = el('span', 'cb-chip');
      chip.appendChild(el('b', null, h.rec.pct + '% off'));
      chip.appendChild(document.createTextNode(' \u00b7 ' + h.rec.label));
      bar.appendChild(chip);
      bar.appendChild(el('span', 'cb-why', h.rec.pct === 100
        ? 'Nothing is due on this order. It still places, and it still lands on the page that says what happens next \u2014 which is the whole point of a code at a hundred per cent.'
        : 'It comes off the price of every line. Where a level takes a deposit, the deposit is then taken on what is left.'));
      bar.appendChild(btn('cb-x', 'Remove', dropCode));
    } else {
      bar.appendChild(el('span', 'cb-chip cb-bad', 'No discount'));
      bar.appendChild(el('span', 'cb-why',
        (h && h.why) || (CODE_NOTE && CODE_NOTE.text) || ''));
      if (h) bar.appendChild(btn('cb-x', 'Clear it', dropCode));
    }
    /* after the title rather than above the breadcrumb: it belongs to the page,
       not to the site furniture, and a reader's eye lands on the heading first. */
    var h1 = main.querySelector('h1');
    if (h1 && h1.nextSibling) { main.insertBefore(bar, h1.nextSibling); }
    else if (h1) { main.appendChild(bar); }
    else { main.insertBefore(bar, main.firstChild); }
  }

  function levelRow(slug, level) {
    var l = LEVELS[level], k = slug + '|' + level, n = S.items[k] || 0;
    var row = el('div', 'lvl' + (n ? ' is-in' : ''));
    var head = el('div', 'lvl-head');
    head.appendChild(el('span', 'lvl-n', String(l.n)));
    head.appendChild(el('span', 'lvl-name', l.name));
    head.appendChild(el('span', 'lvl-price', l.price_label));
    row.appendChild(head);
    row.appendChild(el('p', 'lvl-lede', l.lede));
    var act = el('div', 'lvl-act');
    if (!n) {
      act.appendChild(btn('buy', 'Add to order', function () { add(slug, level, 1); }));
    } else {
      var q = el('div', 'qty');
      q.appendChild(btn('qty-b', '−', function () { add(slug, level, -1); }));
      q.appendChild(el('span', 'qty-n', String(n)));
      q.appendChild(btn('qty-b', '+', function () { add(slug, level, 1); }));
      act.appendChild(q);
      act.appendChild(el('span', 'lvl-in', 'in your order'));
    }
    act.appendChild(el('span', 'lvl-sku', sku(slug, level)));
    row.appendChild(act);
    return row;
  }

  /* ---------------------------------------------------------- the catalogue */
  var FAMILIES = [
    { id: 'all', label: 'Everything' },
    { id: 'code', label: 'Coding agents' },
    { id: 'mail', label: 'Mail and files' },
    { id: 'chat', label: 'Assistants' },
    { id: 'auto', label: 'Automation' },
    { id: 'open', label: 'Open questions' }
  ];

  function familyOf(s) {
    if (/^(code|ci)$/.test(s.family) || /code|actions|scheduled/.test(s.slug)) return 'code';
    if (/mail|drive|dropbox|m365|workspace/.test(s.slug)) return 'mail';
    if (/desktop|web|chatgpt|extension|connector/.test(s.slug)) return 'chat';
    if (/n8n|scheduled|actions/.test(s.slug)) return 'auto';
    return 'chat';
  }

  function visible() {
    var out = M.shapes.filter(function (s) {
      if (S.filter === 'all') return true;
      if (S.filter === 'open') return s.open_questions > 0;
      return familyOf(s) === S.filter;
    });
    out.sort(function (a, b) {
      if (S.sort === 'name') return a.title.localeCompare(b.title);
      if (S.sort === 'grant') return (b.counts ? b.counts.grant : 0) - (a.counts ? a.counts.grant : 0);
      return (b.counts ? b.counts.unbounded : 0) - (a.counts ? a.counts.unbounded : 0);
    });
    return out;
  }

  function tile(s) {
    var c = s.counts || {};
    var t = el('article', 'tile');
    var head = el('div', 'tile-head');
    head.appendChild(el('span', 'tile-glyph', s.glyph));
    var h = el('h3');
    var a = el('a', null, s.title);
    a.href = M.root + 'p/' + s.slug + '/index.html';
    h.appendChild(a);
    head.appendChild(h);
    t.appendChild(head);
    t.appendChild(el('p', 'tile-sum', s.summary));

    var nums = el('div', 'nums');
    [['can do', c.grant], ['wanted', c.wanted], ['not wanted', c.excess],
     ['nothing in the way', c.unbounded]].forEach(function (pair) {
      var d = el('div', 'num');
      d.appendChild(el('b', null, pair[1] == null ? '—' : String(pair[1])));
      d.appendChild(el('span', null, pair[0]));
      nums.appendChild(d);
    });
    t.appendChild(nums);
    if (s.open_questions) {
      t.appendChild(el('p', 'tile-open',
        s.open_questions + ' open question' + (s.open_questions === 1 ? '' : 's') +
        ' — this shape is read from the vendor’s published pages, not measured on the thing itself'));
    }

    var mini = el('div', 'tile-buy');
    M.levels.forEach(function (l) {
      var k = s.slug + '|' + l.id, n = S.items[k] || 0;
      var b = btn('mini' + (n ? ' is-in' : ''), l.price_label + (n > 1 ? ' ×' + n : ''),
                  function () { add(s.slug, l.id, 1); });
      b.title = l.name + ' — ' + l.lede;
      mini.appendChild(b);
    });
    t.appendChild(mini);
    var more = el('a', 'tile-more', 'What each level is →');
    more.href = M.root + 'p/' + s.slug + '/index.html';
    t.appendChild(more);
    return t;
  }

  function renderCatalogue(root) {
    root.textContent = '';
    var bar = el('div', 'shopbar');
    var fam = el('div', 'chips');
    FAMILIES.forEach(function (f) {
      fam.appendChild(btn('chip' + (S.filter === f.id ? ' is-on' : ''), f.label,
                          function () { S.filter = f.id; render(); }));
    });
    bar.appendChild(fam);
    var sorts = el('div', 'chips chips-sort');
    sorts.appendChild(el('span', 'chips-lab', 'Order by'));
    [['unbounded', 'nothing in the way'], ['grant', 'what it can do'], ['name', 'name']]
      .forEach(function (p) {
        sorts.appendChild(btn('chip' + (S.sort === p[0] ? ' is-on' : ''), p[1],
                              function () { S.sort = p[0]; render(); }));
      });
    bar.appendChild(sorts);
    root.appendChild(bar);

    var list = visible();
    /* The published shapes and the catch-all are counted SEPARATELY. They used to
       be one number, so the catalogue said '16 of 16 shapes' while the home page
       said fifteen applications — the one place on this site where two numbers
       about the same thing disagreed, on a site whose argument is that facts come
       from one file so they cannot. Fifteen is the number of published templates;
       the sixteenth tile is a deployment that has no template yet, which is a
       different kind of thing and is now counted as one. */
    var published = 0, catchall = 0;
    M.shapes.forEach(function (s) { if (s.slug === 'your-own') catchall++; else published++; });
    var shownPub = list.filter(function (s) { return s.slug !== 'your-own'; }).length;
    var shownAny = list.length - shownPub;
    root.appendChild(el('p', 'shopcount',
      shownPub + ' of ' + published + ' shapes' +
      (shownAny ? ', and one for a deployment with no template' :
       (catchall ? '' : ''))));
    var grid = el('div', 'tiles');
    list.forEach(function (s) { grid.appendChild(tile(s)); });
    root.appendChild(grid);
  }

  /* ------------------------------------------------------------ one shape */
  function renderShape(root) {
    var s = SHAPES[root.getAttribute('data-shape')];
    if (!s) return;
    root.textContent = '';
    var allowed = s.levels || M.levels.map(function (l) { return l.id; });
    allowed.forEach(function (id) { root.appendChild(levelRow(s.slug, id)); });
  }

  /* ------------------------------------------------------------- the cart */
  function renderCart(root) {
    root.textContent = '';
    var ls = lines();
    if (!ls.length) {
      var empty = el('div', 'cart-empty');
      empty.appendChild(el('p', null, 'Nothing in your order yet.'));
      var go = el('a', 'buy');
      go.href = M.root + 'policies/index.html';
      go.textContent = 'Pick an agent →';
      empty.appendChild(go);
      root.appendChild(empty);
      return;
    }

    var tbl = el('div', 'cartlines');
    ls.forEach(function (l) {
      var row = el('div', 'cartline');
      var d = el('div', 'cl-what');
      d.appendChild(el('b', null, l.shape ? l.shape.title : l.slug));
      d.appendChild(el('span', 'cl-lvl', l.lvl.name));
      d.appendChild(el('span', 'cl-sku', l.sku));
      row.appendChild(d);
      var q = el('div', 'qty');
      q.appendChild(btn('qty-b', '−', function () { add(l.slug, l.level, -1); }));
      q.appendChild(el('span', 'qty-n', String(l.qty)));
      q.appendChild(btn('qty-b', '+', function () { add(l.slug, l.level, 1); }));
      row.appendChild(q);
      var s2 = el('div', 'cl-sum');
      if (l.off > 0) {
        s2.appendChild(el('s', 'cl-was', money(l.list * l.qty)));
        s2.appendChild(document.createTextNode(' '));
      }
      s2.appendChild(el('span', null, money(l.sum)));
      row.appendChild(s2);
      row.appendChild(btn('cl-x', '×', function () { add(l.slug, l.level, -l.qty); }));
      tbl.appendChild(row);
    });
    root.appendChild(tbl);

    var tot = el('div', 'carttotal');
    tot.appendChild(el('span', 'ct-lab', count() + ' item' + (count() === 1 ? '' : 's')));
    if (saved() > 0) {
      var dc = discount();
      tot.appendChild(el('span', 'ct-off',
        '\u2212' + money(saved()) + ' \u00b7 ' + dc.label + ' ' + dc.pct + '%'));
    }
    tot.appendChild(el('span', 'ct-sum', money(total())));
    root.appendChild(tot);

    if (dueLater() > 0) {
      var sp = el('div', 'splitbox');
      sp.appendChild(el('span', 'sp-lab', 'Two of the four levels are somebody\u2019s work, so they take a deposit'));
      var row = el('div', 'sp-row');
      var a = el('div', 'sp-half');
      a.appendChild(el('b', null, money(dueNow())));
      a.appendChild(el('span', null, 'due now'));
      row.appendChild(a);
      var b = el('div', 'sp-half sp-later');
      b.appendChild(el('b', null, money(dueLater())));
      b.appendChild(el('span', null, 'on delivery'));
      row.appendChild(b);
      sp.appendChild(row);
      sp.appendChild(el('p', 'sp-note',
        'The split belongs to the offer, not to how you pay: a card tapped at the stand takes the ' +
        'same deposit as a link opened on a phone. Nothing further is taken until the thing you ' +
        'bought is in your hands.'));
      root.appendChild(sp);
    }

    var acts = el('div', 'cartfoot');
    var go = el('a', 'buy buy-big');
    go.href = M.root + 'pay/index.html';
    go.textContent = (dueNow() === 0 ? 'Place the order \u2014 nothing to pay'
                                     : 'Pay ' + money(dueNow())) + ' \u2192';
    acts.appendChild(go);
    acts.appendChild(btn('linkish', 'Empty the order', function () {
      S.items = {}; S.ref = null; save(); render();
    }));
    var back = el('a', 'linkish');
    back.href = M.root + 'policies/index.html';
    back.textContent = 'Keep looking';
    acts.appendChild(back);
    root.appendChild(acts);

    root.appendChild(orderBox());
  }

  function orderBox() {
    var ord = el('div', 'orderbox');
    ord.appendChild(el('span', 'ob-lab', 'Your order reference'));
    ord.appendChild(el('code', 'ob-ref', ref()));
    ord.appendChild(el('p', 'ob-note',
      'This goes to the payment provider with the amount. It is how the order is matched to the ' +
      'name and contact you give them \u2014 nothing about you is stored here, and this reference ' +
      'lives in this browser until you clear it.'));
    ord.appendChild(el('code', 'ob-line', orderString()));
    ord.appendChild(btn('buy buy-alt', 'Copy the order line', function (e) {
      var b = e.currentTarget, was = b.textContent;
      var done = function (ok) {
        b.textContent = ok ? 'Copied' : 'Select the line above';
        setTimeout(function () { b.textContent = was; }, 1600);
      };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(orderString()).then(
          function () { done(true); }, function () { done(false); });
      } else { done(false); }
    }));
    return ord;
  }

  /* ------------------------------------------------------------- paying ---- */
  function renderPay(root) {
    root.textContent = '';
    var ls = lines();
    if (!ls.length) {
      var e0 = el('div', 'cart-empty');
      e0.appendChild(el('p', null, 'There is nothing to pay for yet.'));
      var g0 = el('a', 'buy');
      g0.href = M.root + 'policies/index.html';
      g0.textContent = 'Pick an agent \u2192';
      e0.appendChild(g0);
      root.appendChild(e0);
      return;
    }

    var sum = el('div', 'paysum');
    var head = el('div', 'paysum-head');
    head.appendChild(el('span', 'ps-lab', 'Due now'));
    head.appendChild(el('span', 'ps-now', money(dueNow())));
    sum.appendChild(head);
    if (dueLater() > 0) {
      sum.appendChild(el('p', 'ps-later',
        money(dueLater()) + ' on delivery \u00b7 ' + money(total()) + ' in total'));
    }
    if (saved() > 0) {
      var dsc = discount();
      sum.appendChild(el('p', 'ps-off',
        dsc.label + ' ' + dsc.pct + '% \u00b7 ' + money(saved()) + ' off ' + money(listTotal()) +
        (dueNow() === 0
          ? '. There is nothing to take, so the order is placed rather than paid for.'
          : '.')));
    }
    var ul = el('ul', 'ps-lines');
    ls.forEach(function (l) {
      var s = splitOf(l);
      var li = el('li');
      li.appendChild(el('span', 'ps-sku', l.sku + (l.qty > 1 ? ' \u00d7' + l.qty : '')));
      li.appendChild(el('span', 'ps-what', (l.shape ? l.shape.title : l.slug) + ' \u2014 ' + l.lvl.name));
      li.appendChild(el('span', 'ps-amt',
        (l.off > 0 ? money(l.list * l.qty) + ' \u2192 ' : '') +
        (s.later > 0 ? money(s.now) + ' now, ' + money(s.later) + ' later' : money(s.now))));
      ul.appendChild(li);
    });
    sum.appendChild(ul);
    sum.appendChild(el('p', 'ps-ref', 'Order reference ' + ref()));
    root.appendChild(sum);

    var w = wallet();
    var rails = el('div', 'rails');
    M.rails.forEach(function (r) {
      var box = el('div', 'rail' + (r.simulated ? ' rail-sim' : ''));
      if (r.simulated) {
        box.appendChild(el('span', 'rail-flag', 'Simulated \u2014 charges nothing'));
      }
      box.appendChild(el('h3', null, r.simulated ? 'Pay from the demonstration wallet' : 'Pay with ' + r.name));
      box.appendChild(el('p', 'rail-kind', r.kind));
      box.appendChild(el('p', 'rail-takes', r.takes));
      if (r.simulated) {
        var bal = el('p', 'rail-bal');
        bal.appendChild(el('b', null, money(w.balance)));
        bal.appendChild(document.createTextNode(' in the wallet'));
        box.appendChild(bal);
        box.appendChild(btn('buy', dueNow() === 0
          ? 'Place the order \u2014 nothing to pay'
          : 'Pay ' + money(dueNow()) + ' from the wallet', function () {
          placeOrder('wallet');
        }));
        box.appendChild(el('p', 'rail-note',
          'Nothing is charged and nothing leaves this browser. The balance is local storage on ' +
          'your own machine and it goes when you clear site data. It tops itself back up when it ' +
          'empties, because the interesting part is the page after this one.'));
      } else if (dueNow() === 0) {
        box.appendChild(el('span', 'buy buy-off', 'Nothing to take'));
        box.appendChild(el('p', 'rail-note',
          'A code took the whole price off, so there is no amount to hand ' + r.name +
          '. Place the order above and it goes through the same flow.'));
      } else if (r.url) {
        var u = r.url + (r.url.indexOf('?') >= 0 ? '&' : '?') +
                encodeURIComponent(r.ref_param) + '=' + encodeURIComponent(orderString());
        if (r.amount_param) {
          u += '&' + encodeURIComponent(r.amount_param) + '=' + (dueNow() / 100).toFixed(2);
        }
        var a2 = el('a', 'buy');
        a2.href = u; a2.rel = 'noopener';
        a2.textContent = 'Pay ' + money(dueNow()) + ' with ' + r.name + ' \u2192';
        box.appendChild(a2);
      } else {
        box.appendChild(el('span', 'buy buy-off', 'No ' + r.name + ' link has been issued yet'));
        box.appendChild(el('p', 'rail-note', r.note));
      }
      rails.appendChild(box);
    });
    root.appendChild(rails);

    var foot = el('div', 'cartfoot');
    var back2 = el('a', 'linkish');
    back2.href = M.root + 'cart/index.html';
    back2.textContent = 'Back to your order';
    foot.appendChild(back2);
    root.appendChild(foot);
  }

  /* ------------------------------------------------ the handover ----------
     THE PAGE AFTER PAYMENT IS NOT ON THIS SITE, and that is deliberate.
     riskmandate.ai publishes one page per level — paid-t1 to paid-t4 — and since
     its v1.19.2 the level-1 page IS the download: the zip, its size, its sha256,
     and a hash check that runs in the buyer's own browser against a manifest its
     build stamps. Copying a size and a hash over here would mean two of each,
     and one of them would go stale the first time a template changed.

     Its contract is two optional plain-text parameters and nothing else. `order`
     is this store's reference, which it shows back and puts in the subject line
     of every mailto on the page. `shape`, at level one only, is the slug of the
     template — the same slug this store uses at /p/<slug>/, which is the whole
     reason the two sites keep their slugs in step. Nothing is posted, there is no
     callback and no session, and the page works with no parameters at all. */
  function handoff(o, line) {
    var lv = LEVELS[line.level];
    if (!lv || !lv.post_url) return '';
    var carries = lv.post_carries || [], q = [];
    /* their rule, applied on this side too: letters, digits, dot, underscore and
       hyphen, at most sixty-four characters. Ours are six and an SG- prefix. */
    if (carries.indexOf('order') >= 0 && o.ref) {
      q.push('order=' + encodeURIComponent(String(o.ref).replace(/[^A-Za-z0-9._-]/g, '').slice(0, 64)));
    }
    if (carries.indexOf('shape') >= 0 && line.slug && SHAPES[line.slug]) {
      q.push('shape=' + encodeURIComponent(line.slug));
    }
    return lv.post_url + (q.length ? '?' + q.join('&') : '');
  }

  /* --------------------------------------------------- after the payment ---- */
  function renderOrder(root) {
    root.textContent = '';
    var o = lastOrder();
    if (!o) {
      var e1 = el('div', 'cart-empty');
      e1.appendChild(el('p', null, 'No order in this browser yet.'));
      var g1 = el('a', 'buy');
      g1.href = M.root + 'policies/index.html';
      g1.textContent = 'Start one \u2192';
      e1.appendChild(g1);
      root.appendChild(e1);
      return;
    }

    var head = el('div', 'orderhead');
    head.appendChild(el('span', 'oh-lab', 'Paid \u00b7 keep this reference'));
    head.appendChild(el('code', 'oh-ref', o.ref));
    var amt = el('p', 'oh-amt');
    amt.appendChild(el('b', null, o.paid_now === 0 ? 'Nothing to pay'
                                                   : money(o.paid_now) + ' paid'));
    if (o.code) {
      amt.appendChild(document.createTextNode(' \u00b7 ' + o.code.label + ' ' + o.code.pct +
        '%, ' + money(o.code.off) + ' off ' + money(o.list_total)));
    }
    if (o.due_later > 0) {
      amt.appendChild(document.createTextNode(' \u00b7 ' + money(o.due_later) +
        ' due on delivery, invoiced when the work is in your hands'));
    }
    head.appendChild(amt);
    if (o.rail === 'wallet') {
      head.appendChild(el('p', 'oh-sim',
        'Paid from the demonstration wallet. Nothing was charged to anybody and nothing left this ' +
        'browser \u2014 this is the flow, not a transaction.'));
    }
    root.appendChild(head);

    o.lines.forEach(function (l) {
      var lv = LEVELS[l.level] || {};
      var card = el('section', 'aftercard');
      var h = el('div', 'ac-head');
      h.appendChild(el('span', 'ac-sku', l.sku + (l.qty > 1 ? ' \u00d7' + l.qty : '')));
      h.appendChild(el('h2', null, l.title));
      h.appendChild(el('span', 'ac-lvl', l.lvl));
      card.appendChild(h);

      var rows = [
        ['What arrives, and when', lv.post_when],
        ['What you do next', lv.post_does],
        ['How the key reaches you', lv.post_key],
        ['Done means', lv.post_done],
        ['How you check that', lv.post_check],
      ];
      var dl = el('div', 'ac-rows');
      rows.forEach(function (r) {
        if (!r[1]) return;
        var row = el('div', 'ac-row');
        row.appendChild(el('span', 'ac-k', r[0]));
        row.appendChild(el('span', 'ac-v', r[1]));
        dl.appendChild(row);
      });
      card.appendChild(dl);

      var go = handoff(o, l);
      if (go) {
        var hv = el('div', 'ac-go');
        var ga = el('a', 'buy buy-big');
        ga.href = go;
        ga.rel = 'noopener';
        ga.textContent = (l.level === 'pack' ? 'Download it now' : 'Open your page for this level') +
          ' \u2192';
        hv.appendChild(ga);
        hv.appendChild(el('p', 'ac-gonote',
          'This opens riskmandate.ai, which is where the vault and the download live. It carries ' +
          'your order reference' + (l.level === 'pack' ? ' and the shape you bought' : '') +
          ', and nothing else \u2014 no account, no session, nothing posted. That page names the ' +
          'mailbox to write to and puts your reference in the subject.'));
        card.appendChild(hv);
      }

      if (lv.prompt) {
        var pw = el('div', 'ac-prompt');
        pw.appendChild(el('span', 'ac-plab', 'The prompt to run'));
        var pre = el('pre', 'ac-pre');
        pre.appendChild(el('code', null, lv.prompt));
        pw.appendChild(pre);
        pw.appendChild(btn('buy buy-alt', 'Copy the prompt', function (e) {
          var b = e.currentTarget, was = b.textContent;
          if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(lv.prompt).then(function () {
              b.textContent = 'Copied';
              setTimeout(function () { b.textContent = was; }, 1600);
            }, function () {});
          }
        }));
        pw.appendChild(el('p', 'ac-pnote',
          'It reads and prints. It does not act, and it asks for no credential \u2014 the last ' +
          'line says so, and that is the line to check before you paste it anywhere.'));
        card.appendChild(pw);
      }
      root.appendChild(card);
    });

    var tail = el('div', 'aftertail');
    tail.appendChild(el('p', null,
      'Keep ' + o.ref + '. It is the reference on your receipt and it is what every message about ' +
      'this order is matched by. If nothing arrives, the page above names a person\u2019s mailbox ' +
      'and puts that reference in the subject for you \u2014 there is no form to fill in, here or there.'));
    var keep = el('a', 'linkish');
    keep.href = M.root + 'policies/index.html';
    keep.textContent = 'Back to the catalogue';
    tail.appendChild(keep);
    root.appendChild(tail);
  }

  /* --------------------------------------------------------------- the bar */
  function renderBadge() { paintBadge(count(), money(total())); }

  function render() {
    var c = document.getElementById('catalogue');
    if (c) renderCatalogue(c);
    var s = document.getElementById('shape-levels');
    if (s) renderShape(s);
    var k = document.getElementById('cart');
    if (k) renderCart(k);
    var pay = document.getElementById('pay');
    if (pay) renderPay(pay);
    var ord = document.getElementById('order');
    if (ord) renderOrder(ord);
    renderCodeBar();
    renderSkuPrices();
    renderPaidRef();
    renderBadge();
  }

  load();
  takeCodeFromAddress();
  render();
})();
