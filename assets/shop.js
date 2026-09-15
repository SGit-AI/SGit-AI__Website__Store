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

  /* What is taken now, and what is owed on delivery. The split is a property of
     the OFFER, not of the rail: a card tapped on a terminal at the stand takes the
     same deposit as a link opened on a phone. Two of the four levels are produced
     without anybody being scheduled and take the whole price; the two that are
     somebody's work take a deposit, because selling an hour of a person from a
     card — for work that has never run for a paying buyer — should not put the
     whole amount on one side of the table before anybody has done anything. */
  function splitOf(line) {
    var pct = line.lvl.pay_now_pct == null ? 100 : line.lvl.pay_now_pct;
    var now = Math.round(line.lvl.price * pct / 100) * line.qty;
    return { now: now, later: line.sum - now, pct: pct };
  }

  function dueNow() {
    return lines().reduce(function (t, l) { return t + splitOf(l).now; }, 0);
  }

  function dueLater() {
    return lines().reduce(function (t, l) { return t + splitOf(l).later; }, 0);
  }

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
    var order = {
      ref: ref(),
      at: new Date().toISOString(),
      rail: railId,
      paid_now: now,
      due_later: dueLater(),
      total: total(),
      lines: lines().map(function (l) {
        var s = splitOf(l);
        return { sku: l.sku, slug: l.slug, level: l.level, qty: l.qty,
                 title: l.shape ? l.shape.title : l.slug, lvl: l.lvl.name,
                 sum: l.sum, now: s.now, later: s.later };
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
    go.textContent = 'Pay ' + money(dueNow()) + ' \u2192';
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
    var ul = el('ul', 'ps-lines');
    ls.forEach(function (l) {
      var s = splitOf(l);
      var li = el('li');
      li.appendChild(el('span', 'ps-sku', l.sku + (l.qty > 1 ? ' \u00d7' + l.qty : '')));
      li.appendChild(el('span', 'ps-what', (l.shape ? l.shape.title : l.slug) + ' \u2014 ' + l.lvl.name));
      li.appendChild(el('span', 'ps-amt',
        s.later > 0 ? money(s.now) + ' now, ' + money(s.later) + ' later' : money(s.now)));
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
        box.appendChild(btn('buy', 'Pay ' + money(dueNow()) + ' from the wallet', function () {
          placeOrder('wallet');
        }));
        box.appendChild(el('p', 'rail-note',
          'Nothing is charged and nothing leaves this browser. The balance is local storage on ' +
          'your own machine and it goes when you clear site data. It tops itself back up when it ' +
          'empties, because the interesting part is the page after this one.'));
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
    amt.appendChild(el('b', null, money(o.paid_now) + ' paid'));
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
      'If nothing arrives, write to a person rather than a form. Quote ' + o.ref + '.'));
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
    renderBadge();
  }

  load();
  render();
})();
