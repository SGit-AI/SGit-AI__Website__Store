/* review.js — the verdict register on /review/.
 *
 * WHAT THIS DOES AND DOES NOT DO. The page is fully rendered before this script
 * runs: every proposal, every stance and every reason box is in the HTML that
 * came off the server, so the page reads with JavaScript off and its markdown twin
 * carries the same argument. This file adds three things and nothing else — it
 * remembers a verdict in the reader's own browser, it counts how many are set, and
 * it puts the result on the clipboard when a button is pressed.
 *
 * NOTHING IS SENT. There is no fetch, no XHR, no beacon and no socket here, and a
 * build check holds every page on this site — this one included — to opening no
 * connection at all. The reason boxes carry no name attribute and there is no form
 * element on the page to submit them. A reader's notes reach us when they paste
 * them to us, and by no other route.
 */
(function () {
  'use strict';

  var modelEl = document.getElementById('review-model');
  if (!modelEl) return;
  var M = JSON.parse(modelEl.textContent);
  var KEY = M.storage;
  var IDS = M.ids;
  var VERDICTS = M.verdicts;

  var state = { items: {}, overall: '' };
  try {
    var raw = window.localStorage.getItem(KEY);
    if (raw) {
      var got = JSON.parse(raw);
      if (got && typeof got === 'object') {
        state.items = got.items || {};
        state.overall = got.overall || '';
      }
    }
  } catch (e) { /* private window, blocked storage */ }

  function save() {
    try { window.localStorage.setItem(KEY, JSON.stringify(state)); }
    catch (e) { /* as above — the page still works, it just forgets */ }
  }

  function answered() {
    var n = 0;
    IDS.forEach(function (id) {
      var s = state.items[id];
      if (s && s.verdict) n++;
    });
    return n;
  }

  function paintProgress() {
    var n = answered();
    var fill = document.getElementById('rv-fill');
    var num = document.getElementById('rv-num');
    if (fill) fill.style.width = Math.round(n / IDS.length * 100) + '%';
    if (num) num.textContent = n + ' of ' + IDS.length + ' answered';
  }

  var flashT = null;
  function flash(node) {
    if (!node) return;
    node.classList.add('on');
    window.clearTimeout(flashT);
    flashT = window.setTimeout(function () { node.classList.remove('on'); }, 1200);
  }

  function paintPicks(id) {
    var cur = (state.items[id] || {}).verdict || null;
    var host = document.querySelector('[data-picks="' + id + '"]');
    if (!host) return;
    Array.prototype.forEach.call(host.querySelectorAll('.rv-pick'), function (b) {
      b.setAttribute('aria-pressed', b.getAttribute('data-v') === cur ? 'true' : 'false');
    });
  }

  IDS.forEach(function (id) {
    var host = document.querySelector('[data-picks="' + id + '"]');
    var why = document.getElementById('why-' + id);
    var saved = document.querySelector('[data-saved="' + id + '"]');
    if (host) {
      Array.prototype.forEach.call(host.querySelectorAll('.rv-pick'), function (b) {
        b.addEventListener('click', function () {
          var v = b.getAttribute('data-v');
          var cur = state.items[id] || {};
          cur.verdict = cur.verdict === v ? null : v;
          state.items[id] = cur;
          save(); paintPicks(id); paintProgress(); flash(saved); refreshPreview();
        });
      });
      paintPicks(id);
    }
    if (why) {
      var s = state.items[id];
      if (s && s.why) why.value = s.why;
      why.addEventListener('input', function () {
        var cur = state.items[id] || {};
        cur.why = why.value;
        state.items[id] = cur;
        save(); flash(saved); refreshPreview();
      });
    }
  });

  var ov = document.getElementById('rv-overall');
  if (ov) {
    if (state.overall) ov.value = state.overall;
    ov.addEventListener('input', function () {
      state.overall = ov.value; save(); refreshPreview();
    });
  }

  /* --------------------------------------------------------------- export */
  function collect() {
    return {
      document: 'Partner review of store.sgit.ai — response register',
      page: M.page,
      site_version: M.version,
      reviewed: M.reviewed_on,
      responded: new Date().toISOString().slice(0, 10),
      answered: answered(),
      total: IDS.length,
      items: IDS.map(function (id) {
        var s = state.items[id] || {};
        var label = null;
        VERDICTS.forEach(function (v) { if (v[0] === s.verdict) label = v[1]; });
        return {
          id: id,
          proposal: M.titles[id],
          answers: M.refs[id],
          our_stance: M.stances[id],
          your_verdict: label,
          your_reason: (s.why || '').trim() || null
        };
      }),
      anything_else: (state.overall || '').trim() || null
    };
  }

  function toMarkdown() {
    var d = collect(), L = [];
    L.push('*Partner review — store.sgit.ai ' + d.site_version + '*');
    L.push(d.page);
    L.push('Answered ' + d.answered + ' of ' + d.total + ' · ' + d.responded);
    L.push('');
    d.items.forEach(function (i) {
      if (!i.your_verdict && !i.your_reason) return;
      L.push(i.id + ' — ' + i.proposal);
      L.push('  ours: ' + i.our_stance + '  |  yours: ' + (i.your_verdict || '—'));
      if (i.your_reason) L.push('  why: ' + i.your_reason);
      L.push('');
    });
    var skipped = d.items.filter(function (i) { return !i.your_verdict && !i.your_reason; });
    if (skipped.length) {
      L.push('Not answered: ' + skipped.map(function (i) { return i.id; }).join(', '));
      L.push('');
    }
    if (d.anything_else) {
      L.push('*Anything the eleven did not cover*');
      L.push(d.anything_else);
    }
    return L.join('\n').trim();
  }

  function toJson() { return JSON.stringify(collect(), null, 2); }

  var toastT = null;
  function toast(msg) {
    var t = document.getElementById('rv-toast');
    if (!t) return;
    t.textContent = msg;
    t.classList.add('on');
    window.clearTimeout(toastT);
    toastT = window.setTimeout(function () { t.classList.remove('on'); }, 2200);
  }

  function refreshPreview() {
    var p = document.getElementById('rv-prev');
    if (p && !p.hidden) p.textContent = toMarkdown() || 'Nothing set yet.';
  }

  /* The clipboard can be refused — a permission, an insecure context, an older
     browser. When it is, the text is shown and selected instead of a failure
     message, because the reader's actual goal is to get it into a message. */
  function copy(text, what) {
    function fallback() {
      var p = document.getElementById('rv-prev');
      var btn = document.getElementById('rv-toggle');
      if (!p) { toast('Could not copy'); return; }
      p.textContent = text;
      p.hidden = false;
      if (btn) btn.textContent = 'Hide what gets copied';
      var r = document.createRange();
      r.selectNodeContents(p);
      var sel = window.getSelection();
      sel.removeAllRanges(); sel.addRange(r);
      p.scrollIntoView({ behavior: 'smooth', block: 'center' });
      toast('Selected below — copy it');
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(
        function () { toast('Copied ' + what); }, fallback);
    } else { fallback(); }
  }

  function on(id, fn) {
    var e = document.getElementById(id);
    if (e) e.addEventListener('click', fn);
  }
  on('rv-md', function () { copy(toMarkdown(), 'as markdown'); });
  on('rv-json', function () { copy(toJson(), 'as JSON'); });
  on('rv-toggle', function () {
    var p = document.getElementById('rv-prev');
    if (!p) return;
    p.hidden = !p.hidden;
    this.textContent = p.hidden ? 'Show what gets copied' : 'Hide what gets copied';
    refreshPreview();
  });
  on('rv-clear', function () {
    if (!window.confirm('Clear every verdict and note on this page? It cannot be undone.')) return;
    state = { items: {}, overall: '' };
    save();
    IDS.forEach(function (id) {
      paintPicks(id);
      var w = document.getElementById('why-' + id);
      if (w) w.value = '';
    });
    if (ov) ov.value = '';
    paintProgress(); refreshPreview(); toast('Cleared');
  });

  paintProgress();
})();
