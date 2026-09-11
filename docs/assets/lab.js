/* lab.js — the configurator behind every prototype in /lab/.
 *
 * ONE ENGINE, FIVE VIEWS. The five prototypes are five interfaces over the same
 * state, the same arithmetic and the same output file. That is what makes them an
 * experiment rather than five drafts: whatever is learned from one applies to the
 * others, and choosing between them is choosing an interface, not a product.
 *
 * NOTHING LEAVES THE BROWSER. There is no network call in this file and there is
 * no form on the page — every control is a button, because this site says it
 * collects nothing from anybody and a gate holds the whole of docs/ to that. The
 * brief lives in local storage until you export it, and exporting it hands the
 * file to you rather than to us.
 *
 * THE PRICE IS NOT COMPUTED. Weighted selections add up, the total lands in a
 * band, and the band names one of the four tiers that already exist and ITS
 * price. A configurator that emitted a number would be inventing a price, which
 * is the first thing the pack says may not be invented.
 */
(function () {
  'use strict';

  var root = document.getElementById('lab');
  var modelEl = document.getElementById('lab-model');
  if (!root || !modelEl) return;

  var M = JSON.parse(modelEl.textContent);
  var VIEW = root.getAttribute('data-view') || 'ladder';
  var KEY = M.meta.storage;
  var SEC = {};
  M.sections.forEach(function (s) { SEC[s.id] = s; });
  var OPT = {};
  M.sections.forEach(function (s) {
    s.options.forEach(function (o) { OPT[s.id + ':' + o.id] = o; });
  });
  var MULTI = M.sections.filter(function (s) { return s.kind === 'multi'; })
                        .map(function (s) { return s.id; });

  /* ------------------------------------------------------------------ state */
  function blank() {
    var st = { track: null, depth: null, scenario: null, step: 0, sel: {}, off: {} };
    MULTI.forEach(function (id) { st.sel[id] = {}; st.off[id] = {}; });
    return st;
  }

  var S = blank();

  function load() {
    try {
      var raw = window.localStorage.getItem(KEY);
      if (!raw) return;
      var got = JSON.parse(raw);
      if (!got || got.schema !== M.meta.schema) return;
      S.track = got.track || null;
      S.depth = got.depth || null;
      S.scenario = got.scenario || null;
      MULTI.forEach(function (id) {
        S.sel[id] = (got.sel && got.sel[id]) || {};
        S.off[id] = (got.off && got.off[id]) || {};
      });
    } catch (e) {
      /* Private windows, blocked site data, a quota that is already full. A
         configurator that throws because it could not remember is worse than one
         that starts empty, so this is the whole of the error handling. */
    }
  }

  function save() {
    try {
      window.localStorage.setItem(KEY, JSON.stringify({
        schema: M.meta.schema, track: S.track, depth: S.depth,
        scenario: S.scenario, sel: S.sel, off: S.off
      }));
    } catch (e) { /* see load() */ }
  }

  /* ------------------------------------------------------------- selections */
  function on(sec, id) { return !!S.sel[sec] && !!S.sel[sec][id]; }

  function picked(sec) {
    return (SEC[sec].options || []).filter(function (o) { return on(sec, o.id); });
  }

  function pickedIds(sec) {
    return picked(sec).map(function (o) { return o.id; });
  }

  /* Naming a surface pre-ticks what that surface normally holds. Unticking one
     afterwards is recorded in `off` rather than forgotten: a grant somebody
     deliberately removed is a stronger statement than one never named, and the
     brief carries it as an assertion the team can check. */
  function applyImplied(surfaceId) {
    var o = OPT['surfaces:' + surfaceId];
    if (!o) return;
    ['grants', 'mandates'].forEach(function (sec) {
      var list = o[sec === 'grants' ? 'implies_grants' : 'implies_mandates'] || [];
      list.forEach(function (id) {
        if (!S.off[sec][id]) S.sel[sec][id] = true;
      });
    });
  }

  function toggle(sec, id) {
    if (SEC[sec].kind === 'single') {
      S.depth = (S.depth === id ? null : id);
      commit();
      return;
    }
    if (on(sec, id)) {
      delete S.sel[sec][id];
      if (sec === 'grants' || sec === 'mandates') S.off[sec][id] = true;
    } else {
      S.sel[sec][id] = true;
      delete S.off[sec][id];
      if (sec === 'surfaces') applyImplied(id);
    }
    commit();
  }

  function loadScenario(sid) {
    var sc = null;
    M.scenarios.forEach(function (x) { if (x.id === sid) sc = x; });
    if (!sc) return;
    S = blank();
    S.track = sc.track;
    S.depth = sc.depth;
    S.scenario = sc.id;
    MULTI.forEach(function (sec) {
      (sc[sec] || []).forEach(function (id) { S.sel[sec][id] = true; });
    });
    S.step = 1;
    commit();
  }

  function reset() { S = blank(); commit(); }

  /* ----------------------------------------------------------- the arithmetic */
  function total() {
    var t = 0;
    MULTI.forEach(function (sec) { t += picked(sec).length * SEC[sec].weight; });
    if (S.depth && OPT['depth:' + S.depth]) t += (OPT['depth:' + S.depth].weight || 0);
    return t;
  }

  /* Two things decide the band, and the second one matters more.
     COUNT decides the width: more of the estate described is more to map.
     THE DELIVERABLE decides the minimum: asking for a team assessment cannot land
     below the tier that IS a team assessment, however short the list is. Without
     the floor, four of the five prebaked scenarios landed on the same tier and the
     price stopped responding to what was actually being asked for. */
  var TIER_ORDER = ['t1', 't2', 't3', 't4'];

  function countedBand() {
    var t = total(), found = M.bands[M.bands.length - 1];
    for (var i = 0; i < M.bands.length; i++) {
      if (t <= M.bands[i].up_to) { found = M.bands[i]; break; }
    }
    return found;
  }

  function floorBand() {
    var idx = -1;
    picked('wants').forEach(function (o) {
      var k = TIER_ORDER.indexOf(o.offer);
      if (k > idx) idx = k;
    });
    if (idx < 0) return null;
    var want = TIER_ORDER[idx], out = null;
    M.bands.forEach(function (b) { if (b.offer === want) out = b; });
    return out;
  }

  function band() {
    var counted = countedBand(), floor = floorBand();
    if (floor && M.bands.indexOf(floor) > M.bands.indexOf(counted)) {
      return floor;
    }
    return counted;
  }

  function bandSetBy() {
    var counted = countedBand(), floor = floorBand();
    if (floor && M.bands.indexOf(floor) > M.bands.indexOf(counted)) {
      return 'the deliverable asked for';
    }
    return 'the size of what was described';
  }

  function offerOf(band) { return M.offers[band.offer]; }

  /* A grant is EXCESS when it is permitted and no mandate you selected would need
     it. The edges are in data/brief.yml, so a reader who disagrees can disagree
     with a specific edge rather than with a verdict. */
  function excess() {
    var mandates = pickedIds('mandates');
    return picked('grants').filter(function (g) {
      var by = g.justified_by || [];
      for (var i = 0; i < by.length; i++) {
        if (mandates.indexOf(by[i]) >= 0) return false;
      }
      return true;
    });
  }

  /* What this brief could NOT establish. It is part of the output rather than a
     warning strip, because a brief that names its own gaps is worth more to the
     team reading it than one that reads as complete and is not. */
  function unknowns() {
    var out = [];
    var g = picked('grants'), m = picked('mandates'), w = pickedIds('wants');
    if (!S.track) out.push('No track chosen, so the brief does not say which side the map is drawn from.');
    if (!picked('surfaces').length) out.push('No surface named. Nothing can be mapped, and a map of nothing is not a deliverable.');
    if (g.length && !m.length) {
      out.push('The permitted half is filled in and the expected half is empty, so no delta can be computed. That is the most common shape this arrives in and it is a finding, not a blank.');
    }
    if (on('mandates', 'none-written')) {
      out.push('Nothing is written down about what these are supposed to do. The expected half of the map will be built from what people say in the room, and the brief will mark it as such.');
    }
    if (!S.depth || S.depth === 'declared') {
      out.push('Nothing here is measured: every line is your account of your own estate, and anything built from it says so on its face.');
    }
    picked('surfaces').forEach(function (s) {
      (s.implies_grants || []).forEach(function (gid) {
        if (S.off.grants[gid]) {
          out.push('"' + s.label + '" normally carries "' + OPT['grants:' + gid].label +
                   '" and you removed it. Recorded as an assertion to check first.');
        }
      });
    });
    w.forEach(function (id) {
      var o = OPT['wants:' + id];
      if (o && o.offer && M.offers[o.offer] && M.offers[o.offer].caveat) {
        out.push(M.offers[o.offer].caveat);
      }
    });
    return out;
  }

  function brief() {
    var b = band(), offer = offerOf(b);
    var tr = null;
    M.tracks.forEach(function (t) { if (t.id === S.track) tr = t; });
    return {
      brief: 'store.sgit.ai',
      schema: M.meta.schema,
      site_version: M.version,
      prototype: VIEW,
      generated: new Date().toISOString(),
      started_from: S.scenario || 'blank',
      track: S.track,
      track_frame: tr ? tr.frame : null,
      estate: picked('surfaces').map(function (o) {
        return { id: o.id, label: o.label,
                 normally_carries: o.implies_grants || [] };
      }),
      granted: picked('grants').map(function (o) {
        return { id: o.id, label: o.label, justified_by: o.justified_by || [] };
      }),
      mandated: picked('mandates').map(function (o) {
        return { id: o.id, label: o.label };
      }),
      excess_authority: excess().map(function (o) {
        return { id: o.id, label: o.label,
                 why: 'Permitted, and no mandate on this brief would need it.' };
      }),
      removed: {
        grants: Object.keys(S.off.grants || {}),
        mandates: Object.keys(S.off.mandates || {})
      },
      deliverables: picked('wants').map(function (o) {
        return { id: o.id, label: o.label, gives: o.gives || '',
                 offer: o.offer || null,
                 state: o.offer && M.offers[o.offer] ? M.offers[o.offer].state : null };
      }),
      evidence: S.depth,
      weight: { total: total(), by_section: MULTI.reduce(function (a, sec) {
        a[sec] = picked(sec).length * SEC[sec].weight; return a;
      }, {}) },
      band: { id: b.id, says: b.says, offer: b.offer, set_by: bandSetBy(),
              price: offer.price, rail: offer.rail, delivery: offer.delivery },
      unknowns: unknowns(),
      note: 'A brief, not an order and not an assessment. Nothing in it has been checked by anybody. It is the starting point a team would otherwise spend a first call assembling.'
    };
  }

  /* --------------------------------------------------------------- elements */
  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }

  function optButton(sec, o) {
    var b = el('button', 'opt' + (on(sec, o.id) ? ' is-on' : ''));
    b.type = 'button';
    b.setAttribute('aria-pressed', on(sec, o.id) ? 'true' : 'false');
    b.appendChild(el('span', 'opt-l', o.label));
    if (o.note) b.appendChild(el('span', 'opt-n', o.note));
    if (o.gives) b.appendChild(el('span', 'opt-n', o.gives));
    if (o.offer && M.offers[o.offer] && M.offers[o.offer].chip) {
      var c = el('span', 'opt-state', M.offers[o.offer].chip);
      b.appendChild(c);
    }
    b.addEventListener('click', function () { toggle(sec, o.id); });
    return b;
  }

  function optGrid(sec, ids) {
    var s = SEC[sec];
    var wrap = el('div', 'opts');
    (s.options || []).forEach(function (o) {
      if (ids && ids.indexOf(o.id) < 0) return;
      wrap.appendChild(optButton(sec, o));
    });
    return wrap;
  }

  function sectionHead(sec) {
    var s = SEC[sec];
    var h = el('div', 'sec-head');
    h.appendChild(el('span', 'sec-n', String(s.n)));
    h.appendChild(el('h2', null, s.title));
    h.appendChild(el('p', 'sec-q', s.question));
    h.appendChild(el('p', 'sec-why', s.why));
    return h;
  }

  function trackButtons() {
    var wrap = el('div', 'opts opts-track');
    M.tracks.forEach(function (t) {
      var b = el('button', 'opt opt-track' + (S.track === t.id ? ' is-on' : ''));
      b.type = 'button';
      b.setAttribute('aria-pressed', S.track === t.id ? 'true' : 'false');
      b.appendChild(el('span', 'opt-v', t.verb));
      b.appendChild(el('span', 'opt-l', t.label));
      b.appendChild(el('span', 'opt-n', t.story));
      b.addEventListener('click', function () {
        S.track = (S.track === t.id ? null : t.id);
        if (S.track) {
          var tr = t;
          (tr.defaults || []).forEach(function (id) { S.sel.wants[id] = true; });
        }
        commit();
      });
      wrap.appendChild(b);
    });
    return wrap;
  }

  function scenarioButtons(filterTrack) {
    var wrap = el('div', 'opts opts-scn');
    M.scenarios.forEach(function (sc) {
      if (filterTrack && S.track && sc.track !== S.track) return;
      var b = el('button', 'opt opt-scn' + (S.scenario === sc.id ? ' is-on' : ''));
      b.type = 'button';
      b.appendChild(el('span', 'opt-l', sc.label));
      b.appendChild(el('span', 'opt-n', sc.note));
      b.appendChild(el('span', 'opt-c',
        sc.surfaces.length + ' surfaces · ' + sc.grants.length + ' grants · ' +
        sc.mandates.length + ' mandates'));
      b.addEventListener('click', function () { loadScenario(sc.id); });
      wrap.appendChild(b);
    });
    return wrap;
  }

  /* ------------------------------------------------------------- the ticket */
  function ticket() {
    var b = band(), offer = offerOf(b), ex = excess(), un = unknowns();
    var t = el('aside', 'ticket');

    var head = el('div', 'ticket-head');
    head.appendChild(el('span', 'ticket-k', 'Where this lands'));
    head.appendChild(el('span', 'ticket-price', offer.price));
    head.appendChild(el('span', 'ticket-tier', offer.label));
    t.appendChild(head);
    t.appendChild(el('p', 'ticket-says', b.says));
    if (offer.deposit) {
      var dep = el('p', 'ticket-says');
      dep.appendChild(el('b', null, offer.deposit + ' deposit'));
      dep.appendChild(document.createTextNode(
        ' is the first payable amount. The balance is invoiced after a conversation.'));
      t.appendChild(dep);
    }

    var meter = el('div', 'meter');
    var fill = el('i');
    var pct = Math.min(100, Math.round(total() / 40 * 100));
    fill.style.width = pct + '%';
    meter.appendChild(fill);
    t.appendChild(meter);
    t.appendChild(el('p', 'ticket-w',
      total() + ' points from ' + MULTI.map(function (sec) {
        return picked(sec).length + ' ' + sec;
      }).join(', ') + (S.depth ? ', ' + OPT['depth:' + S.depth].label.toLowerCase() : '')));
    t.appendChild(el('p', 'ticket-w', 'Set by ' + bandSetBy() + '.'));

    var rows = el('ul', 'ticket-rows');
    MULTI.forEach(function (sec) {
      var li = el('li');
      li.appendChild(el('b', null, String(picked(sec).length)));
      li.appendChild(el('span', null, ' ' + SEC[sec].title.toLowerCase()));
      rows.appendChild(li);
    });
    t.appendChild(rows);

    if (ex.length) {
      var d = el('div', 'ticket-delta');
      d.appendChild(el('b', null, ex.length + ' permitted and not expected'));
      var ul = el('ul');
      ex.slice(0, 6).forEach(function (o) { ul.appendChild(el('li', null, o.label)); });
      d.appendChild(ul);
      d.appendChild(el('p', 'small', 'This list is the delta. It is what the work is for.'));
      t.appendChild(d);
    }

    if (un.length) {
      var u = el('div', 'ticket-un');
      u.appendChild(el('b', null, un.length + ' thing' + (un.length === 1 ? '' : 's') + ' this brief cannot establish'));
      var ul2 = el('ul');
      un.slice(0, 4).forEach(function (x) { ul2.appendChild(el('li', null, x)); });
      if (un.length > 4) ul2.appendChild(el('li', 'dim', 'and ' + (un.length - 4) + ' more, in the file'));
      u.appendChild(ul2);
      t.appendChild(u);
    }

    var acts = el('div', 'ticket-acts');
    var dl = el('button', 'buy', 'Download the brief');
    dl.type = 'button';
    dl.addEventListener('click', download);
    acts.appendChild(dl);

    var cp = el('button', 'buy buy-alt', 'Copy as JSON');
    cp.type = 'button';
    cp.addEventListener('click', function () { copy(cp); });
    acts.appendChild(cp);

    var go = el('a', 'buy buy-alt');
    /* M.root is this page's distance from the site root, written in by the build.
       Every link here is relative for the same reason every link in the HTML is:
       the site has to work on the custom domain, on a project path, from a local
       directory, and inside a frame with no origin at all. */
    go.href = M.root + (offer.delivery || 'offers/index.html');
    go.textContent = 'What arrives for ' + offer.price + ' →';
    acts.appendChild(go);

    var rs = el('button', 'linkish', 'Start again');
    rs.type = 'button';
    rs.addEventListener('click', reset);
    acts.appendChild(rs);
    t.appendChild(acts);

    t.appendChild(el('p', 'ticket-foot',
      'Nothing on this page is bought, and nothing here has been checked by anybody. ' +
      'The brief is written to this browser and stays there until you export it.'));
    return t;
  }

  function download() {
    var text = JSON.stringify(brief(), null, 2);
    var blob = new Blob([text], { type: 'application/json' });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = 'agent-brief-' + (S.track || 'draft') + '.json';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
  }

  function copy(btn) {
    var text = JSON.stringify(brief(), null, 2);
    var was = btn.textContent;
    var done = function (ok) {
      btn.textContent = ok ? 'Copied' : 'Select it below instead';
      setTimeout(function () { btn.textContent = was; }, 1600);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(function () { done(true); },
                                               function () { done(false); });
    } else {
      done(false);
    }
    var pre = document.getElementById('lab-json');
    if (pre) pre.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

  function jsonPanel() {
    var wrap = el('details', 'jsonwrap');
    var sum = el('summary', null, 'The brief, as the file it becomes');
    wrap.appendChild(sum);
    wrap.appendChild(el('p', 'small dim',
      'This is the whole output. It is what a team would be handed, and it is the ' +
      'thing the rest of this is for — the page is a way of writing it, not a product ' +
      'of its own.'));
    var pre = el('pre', 'json');
    pre.id = 'lab-json';
    pre.appendChild(el('code', null, JSON.stringify(brief(), null, 2)));
    wrap.appendChild(pre);
    if (sessionOpen) wrap.open = true;
    wrap.addEventListener('toggle', function () { sessionOpen = wrap.open; });
    return wrap;
  }
  var sessionOpen = false;

  /* ----------------------------------------------------------------- views */
  function viewLadder(main) {
    main.appendChild(trackHint());
    main.appendChild(trackSection());
    M.sections.forEach(function (s) {
      var w = el('section', 'lab-sec');
      w.appendChild(sectionHead(s.id));
      w.appendChild(optGrid(s.id));
      main.appendChild(w);
    });
    main.appendChild(jsonPanel());
  }

  function viewInterview(main) {
    var steps = [{ id: 'track' }].concat(M.sections.map(function (s) { return { id: s.id }; }));
    var i = Math.max(0, Math.min(S.step || 0, steps.length - 1));
    var cur = steps[i];

    var bar = el('div', 'steps');
    steps.forEach(function (s, n) {
      var d = el('button', 'step' + (n === i ? ' is-on' : '') + (n < i ? ' is-done' : ''));
      d.type = 'button';
      d.textContent = n === 0 ? 'Who' : SEC[s.id].title;
      d.addEventListener('click', function () { S.step = n; commit(); });
      bar.appendChild(d);
    });
    main.appendChild(bar);

    var stage = el('section', 'lab-sec lab-stage');
    if (cur.id === 'track') {
      stage.appendChild(el('h2', null, 'Who is asking'));
      stage.appendChild(el('p', 'sec-q', 'The same estate, mapped from three different sides. It changes the order of every question after this one.'));
      stage.appendChild(trackButtons());
    } else {
      stage.appendChild(sectionHead(cur.id));
      stage.appendChild(optGrid(cur.id));
    }
    main.appendChild(stage);

    var nav = el('div', 'stepnav');
    if (i > 0) {
      var prev = el('button', 'buy buy-alt', '← Back');
      prev.type = 'button';
      prev.addEventListener('click', function () { S.step = i - 1; commit(); });
      nav.appendChild(prev);
    }
    if (i < steps.length - 1) {
      var next = el('button', 'buy', 'Next →');
      next.type = 'button';
      next.addEventListener('click', function () { S.step = i + 1; commit(); });
      nav.appendChild(next);
    } else {
      nav.appendChild(el('span', 'small dim', 'That is the whole brief. The panel beside it is the file.'));
    }
    main.appendChild(nav);
    main.appendChild(jsonPanel());
  }

  function viewBoard(main) {
    main.appendChild(trackHint());
    main.appendChild(trackSection());
    var pick = el('section', 'lab-sec');
    pick.appendChild(sectionHead('surfaces'));
    pick.appendChild(optGrid('surfaces'));
    main.appendChild(pick);

    var board = el('section', 'lab-sec');
    board.appendChild(el('h2', null, 'The estate, one card per surface'));
    board.appendChild(el('p', 'sec-why',
      'Each card carries what that surface normally holds. A grant in red is permitted ' +
      'with nothing on this brief that would need it.'));
    var cards = el('div', 'board');
    var chosen = picked('surfaces');
    if (!chosen.length) {
      cards.appendChild(el('p', 'dim', 'Nothing named yet. Pick a surface above and it appears here.'));
    }
    var exIds = excess().map(function (o) { return o.id; });
    chosen.forEach(function (s) {
      var c = el('div', 'bcard');
      c.appendChild(el('h3', null, s.label));
      c.appendChild(el('p', 'small dim', s.note || ''));
      var gl = el('ul', 'blist');
      (s.implies_grants || []).forEach(function (gid) {
        if (!on('grants', gid)) return;
        var li = el('li', exIds.indexOf(gid) >= 0 ? 'is-excess' : null,
                    OPT['grants:' + gid].label);
        gl.appendChild(li);
      });
      if (!gl.children.length) gl.appendChild(el('li', 'dim', 'no grant ticked'));
      c.appendChild(el('span', 'blab', 'permits'));
      c.appendChild(gl);
      var ml = el('ul', 'blist');
      (s.implies_mandates || []).forEach(function (mid) {
        if (on('mandates', mid)) ml.appendChild(el('li', null, OPT['mandates:' + mid].label));
      });
      if (!ml.children.length) ml.appendChild(el('li', 'dim', 'nothing expected written down'));
      c.appendChild(el('span', 'blab', 'expected to'));
      c.appendChild(ml);
      cards.appendChild(c);
    });
    board.appendChild(cards);
    main.appendChild(board);

    ['grants', 'mandates', 'wants', 'depth'].forEach(function (id) {
      var w = el('section', 'lab-sec');
      w.appendChild(sectionHead(id));
      w.appendChild(optGrid(id));
      main.appendChild(w);
    });
    main.appendChild(jsonPanel());
  }

  function viewDelta(main) {
    main.appendChild(trackHint());
    main.appendChild(trackSection());
    var head = el('section', 'lab-sec');
    head.appendChild(el('h2', null, 'Permitted, expected, and the gap'));
    head.appendChild(el('p', 'sec-why',
      'Tick the left column for what the credentials permit and the right for what ' +
      'anybody actually expects. The middle fills itself: it is what is permitted with ' +
      'nothing on this brief that would need it. That column is the product.'));
    main.appendChild(head);

    var cols = el('div', 'delta3');
    var left = el('div', 'dcol');
    left.appendChild(el('h3', null, 'Permitted'));
    left.appendChild(optGrid('grants'));
    cols.appendChild(left);

    var mid = el('div', 'dcol dcol-mid');
    mid.appendChild(el('h3', null, 'Excess authority'));
    var ex = excess();
    if (!ex.length) {
      mid.appendChild(el('p', 'dim',
        pickedIds('grants').length
          ? 'Nothing, on what is ticked so far.'
          : 'Nothing ticked yet on either side.'));
    }
    ex.forEach(function (o) {
      var d = el('div', 'dx');
      d.appendChild(el('b', null, o.label));
      d.appendChild(el('span', null, 'permitted, and nothing here would need it'));
      mid.appendChild(d);
    });
    cols.appendChild(mid);

    var right = el('div', 'dcol');
    right.appendChild(el('h3', null, 'Expected'));
    right.appendChild(optGrid('mandates'));
    cols.appendChild(right);
    main.appendChild(cols);

    ['surfaces', 'wants', 'depth'].forEach(function (id) {
      var w = el('section', 'lab-sec');
      w.appendChild(sectionHead(id));
      w.appendChild(optGrid(id));
      main.appendChild(w);
    });
    main.appendChild(jsonPanel());
  }

  function viewScenario(main) {
    var head = el('section', 'lab-sec');
    head.appendChild(el('h2', null, 'Start from the one that looks most like you'));
    head.appendChild(el('p', 'sec-why',
      'Five shapes people arrive in. Each is a HYPOTHESIS rather than a survey ' +
      'finding — nobody has counted how common they are — so the brief records which ' +
      'one it started from, and the team reading it can tell what was assumed from ' +
      'what was answered.'));
    head.appendChild(scenarioButtons(false));
    main.appendChild(head);
    main.appendChild(trackSection());

    if (S.scenario) {
      var diff = el('section', 'lab-sec');
      diff.appendChild(el('h2', null, 'Now correct it'));
      diff.appendChild(el('p', 'sec-why',
        'Everything below was filled in by the scenario. What you change is the ' +
        'interesting part, and the brief keeps a record of what you removed.'));
      main.appendChild(diff);
      M.sections.forEach(function (s) {
        var w = el('section', 'lab-sec');
        w.appendChild(sectionHead(s.id));
        w.appendChild(optGrid(s.id));
        main.appendChild(w);
      });
    }
    main.appendChild(jsonPanel());
  }

  /* Every view needs this, and two of them shipped without it: the board and the
     delta rendered the frame sentence but no way to choose a frame, so `track` was
     null in the brief and the page said "Pick who is asking" beside nothing that
     could be picked. Found by driving the pages rather than by reading them. */
  function trackSection() {
    var sec = el('section', 'lab-sec');
    sec.appendChild(el('h2', null, 'Who is asking'));
    sec.appendChild(el('p', 'sec-q',
      'The same estate, mapped from three different sides. It changes the frame of ' +
      'every question after this one.'));
    sec.appendChild(trackButtons());
    return sec;
  }

  function trackHint() {
    var tr = null;
    M.tracks.forEach(function (t) { if (t.id === S.track) tr = t; });
    var p = el('p', 'trackhint');
    p.textContent = tr ? tr.frame : 'Pick who is asking and the rest of the page changes its frame.';
    return p;
  }

  var VIEWS = { ladder: viewLadder, interview: viewInterview, board: viewBoard,
                delta: viewDelta, scenario: viewScenario };

  /* ------------------------------------------------------------------ render */
  function commit() { save(); render(); }

  function render() {
    root.textContent = '';
    var wrap = el('div', 'lab-wrap');
    var main = el('div', 'lab-main');
    (VIEWS[VIEW] || viewLadder)(main);
    wrap.appendChild(main);
    wrap.appendChild(ticket());
    root.appendChild(wrap);
  }

  /* A second entry point, for a page that hosts more than one prototype in place.
     On the site each prototype has its own URL and a brief follows between them
     through local storage, so switching is just a link. In a single page — the
     preview of all five, side by side — the view has to change without one. */
  window.SGitLab = {
    view: function () { return VIEW; },
    views: Object.keys(VIEWS),
    setView: function (v) {
      if (!VIEWS[v]) return false;
      VIEW = v;
      root.setAttribute('data-view', v);
      render();
      return true;
    }
  };

  load();
  render();
})();
