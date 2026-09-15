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

  function paintBadge(n, label) {
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
    return Object.keys(S.items).map(function (k) {
      var p = k.split('|'), slug = p[0], level = p[1];
      return { slug: slug, level: level, qty: S.items[k],
               shape: SHAPES[slug], lvl: LEVELS[level],
               sku: sku(slug, level), sum: LEVELS[level].price * S.items[k] };
    }).sort(function (a, b) { return a.lvl.n - b.lvl.n || a.slug.localeCompare(b.slug); });
  }

  function total() {
    return lines().reduce(function (t, l) { return t + l.sum; }, 0);
  }

  function count() {
    return lines().reduce(function (t, l) { return t + l.qty; }, 0);
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
    root.appendChild(el('p', 'shopcount',
      list.length + ' of ' + M.shapes.length + ' shapes'));
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
      row.appendChild(el('div', 'cl-sum', money(l.sum)));
      row.appendChild(btn('cl-x', '×', function () { add(l.slug, l.level, -l.qty); }));
      tbl.appendChild(row);
    });
    root.appendChild(tbl);

    var tot = el('div', 'carttotal');
    tot.appendChild(el('span', 'ct-lab', count() + ' item' + (count() === 1 ? '' : 's')));
    tot.appendChild(el('span', 'ct-sum', money(total())));
    root.appendChild(tot);

    // the order reference, which is the whole integration
    var ord = el('div', 'orderbox');
    ord.appendChild(el('span', 'ob-lab', 'Your order reference'));
    ord.appendChild(el('code', 'ob-ref', ref()));
    ord.appendChild(el('p', 'ob-note',
      'This goes to the payment provider with the amount. It is how the order is ' +
      'matched to the name and contact you give them — nothing about you is ' +
      'stored here, and this reference lives in this browser until you clear it.'));
    var line = el('code', 'ob-line', orderString());
    ord.appendChild(line);
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
    root.appendChild(ord);

    var rails = el('div', 'rails');
    M.rails.forEach(function (r) {
      var box = el('div', 'rail');
      box.appendChild(el('span', 'rail-n', String(r.n)));
      box.appendChild(el('h3', null, 'Pay with ' + r.name));
      box.appendChild(el('p', 'rail-kind', r.kind));
      box.appendChild(el('p', 'rail-takes', r.takes));
      if (r.url) {
        var u = r.url + (r.url.indexOf('?') >= 0 ? '&' : '?') +
                encodeURIComponent(r.ref_param) + '=' + encodeURIComponent(orderString());
        if (r.amount_param) {
          u += '&' + encodeURIComponent(r.amount_param) + '=' + (total() / 100).toFixed(2);
        }
        var a = el('a', 'buy');
        a.href = u;
        a.rel = 'noopener';
        a.textContent = 'Pay ' + money(total()) + ' with ' + r.name + ' →';
        box.appendChild(a);
      } else {
        box.appendChild(el('span', 'buy buy-off',
          'No ' + r.name + ' link has been issued yet'));
        box.appendChild(el('p', 'rail-note', r.note));
      }
      rails.appendChild(box);
    });
    root.appendChild(rails);

    var foot = el('div', 'cartfoot');
    foot.appendChild(btn('linkish', 'Empty the order', function () {
      S.items = {}; S.ref = null; save(); render();
    }));
    var back = el('a', 'linkish');
    back.href = M.root + 'policies/index.html';
    back.textContent = 'Keep looking';
    foot.appendChild(back);
    root.appendChild(foot);
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
    renderBadge();
  }

  load();
  render();
})();
