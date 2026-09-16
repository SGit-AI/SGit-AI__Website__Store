/* describe-your-agent — the two prototypes, one model.
 *
 * WHAT THIS PRODUCES IS THE GRANT: everything the agent can do. It is one of the
 * four objects in an Agent Behaviour Policy and the page says so, because a
 * reader who thought this was the whole document would be getting three quarters
 * of the £500 level for nothing in their own head.
 *
 * NOTHING LEAVES THIS BROWSER. There is no fetch, no beacon and no socket in this
 * file and a build check refuses one. What you build goes to the clipboard or to
 * your downloads, which are the only two routes that do not require this site to
 * become something it is not.
 *
 * ONE VOCABULARY, TWO INTERFACES. Both prototypes render the same twenty-three
 * primitives out of the same island and emit the same document. That is what
 * makes them an experiment rather than two drafts.
 */
(function () {
  'use strict';
  var island = document.getElementById('agent-model');
  if (!island) return;
  var M = JSON.parse(island.textContent);
  var BY_ID = {};
  M.capabilities.forEach(function (c) { BY_ID[c.id] = c; });

  var root = document.querySelector('.ag');
  if (!root) return;
  var mode = root.getAttribute('data-mode');
  var chosen = [];

  function load() {
    try {
      var got = JSON.parse(window.localStorage.getItem(M.storage) || 'null');
      if (got && Array.isArray(got.capabilities)) {
        chosen = got.capabilities.filter(function (id) { return BY_ID[id]; });
      }
    } catch (e) { /* private window, blocked storage — start empty */ }
  }
  function save() {
    try {
      window.localStorage.setItem(M.storage, JSON.stringify({ capabilities: chosen }));
    } catch (e) { /* nothing to do; the page still works for this visit */ }
  }

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }

  /* The document. This is the product — the canvas is only how it gets filled in.
     It carries the grammar and the reach glossary with it, because the session
     that reads it should not have to guess what `world` means. */
  function definition() {
    var caps = chosen.map(function (id) {
      var c = BY_ID[id];
      return { id: c.id, verb: c.verb, object: c.object, reach: c.reach,
               family: c.family, undo: c.undo, gloss: c.gloss };
    });
    var irreversible = caps.filter(function (c) { return c.undo === 'no'; });
    return {
      what_this_is: 'The GRANT half of an Agent Behaviour Policy: everything this agent can do, ' +
        'as described by the person who runs it. It is not the mandate, not the delta and not a ' +
        'policy.',
      grammar: M.grammar,
      reaches: M.reaches,
      // wherever this page is: the lab's two prototypes, or the store's own page
      described_on: 'store.sgit.ai' + location.pathname.replace(/index\.html$/, ''),
      prototype: true,
      count: caps.length,
      irreversible_count: irreversible.length,
      capabilities: caps,
      not_selected: M.capabilities.length - caps.length,
      note: 'Selected by hand rather than measured. MAP-A-GRANT.md, which ships in every public ' +
        'template pack, measures the same thing from the deployment and will disagree with this ' +
        'wherever somebody guessed.'
    };
  }

  function markdown() {
    var d = definition(), L = [];
    L.push('# What this agent can do');
    L.push('');
    L.push(d.what_this_is);
    L.push('');
    L.push('- Grammar: `' + d.grammar + '`');
    L.push('- Selected: ' + d.count + ' of ' + M.capabilities.length);
    L.push('- Not undoable: ' + d.irreversible_count);
    L.push('- Described by hand, not measured. MAP-A-GRANT.md measures the same thing from the ' +
           'deployment and will disagree wherever somebody guessed.');
    L.push('');
    L.push('## Capabilities');
    L.push('');
    d.capabilities.forEach(function (c) {
      L.push('- `' + c.id + '` — ' + c.gloss + ' _(undo: ' + c.undo + ')_');
    });
    L.push('');
    L.push('## What reach means');
    L.push('');
    Object.keys(d.reaches).forEach(function (k) {
      L.push('- `' + k + '` — ' + d.reaches[k]);
    });
    return L.join('\n');
  }

  function renderList() {
    var box = root.querySelector('[data-ag-list]');
    var count = root.querySelector('[data-ag-count]');
    if (!box) return;
    box.textContent = '';
    if (!chosen.length) {
      box.appendChild(el('p', 'dim', 'Nothing selected. Click a capability above.'));
      if (count) count.textContent = 'nothing yet';
      return;
    }
    var irr = chosen.filter(function (id) { return BY_ID[id].undo === 'no'; }).length;
    if (count) {
      count.textContent = chosen.length + (chosen.length === 1 ? ' capability' : ' capabilities') +
        (irr ? ' · ' + irr + ' not undoable' : '');
    }
    var ul = el('ul', 'ag-chosen');
    chosen.forEach(function (id) {
      var c = BY_ID[id];
      var li = el('li', 'u-' + (c.undo === 'yes' ? 'y' : c.undo === 'no' ? 'n' : 'e'));
      li.appendChild(el('b', null, c.gloss));
      li.appendChild(el('code', null, c.id));
      ul.appendChild(li);
    });
    box.appendChild(ul);
  }

  function renderChips() {
    Array.prototype.forEach.call(root.querySelectorAll('.cap'), function (b) {
      var on = chosen.indexOf(b.getAttribute('data-cap')) >= 0;
      b.setAttribute('aria-pressed', on ? 'true' : 'false');
    });
  }

  function toggle(id) {
    var i = chosen.indexOf(id);
    if (i >= 0) { chosen.splice(i, 1); } else { chosen.push(id); }
    save();
    renderChips();
    renderList();
  }

  function copyOut(text, btn) {
    var done = function () {
      var was = btn.textContent;
      btn.textContent = 'Copied';
      window.setTimeout(function () { btn.textContent = was; }, 1400);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done, function () { fallback(text, done); });
    } else { fallback(text, done); }
  }
  function fallback(text, done) {
    /* No textarea is left in the document: this site has one typing surface and it
       is not here. The node is created, used and removed inside one turn. */
    var ta = document.createElement('textarea');
    ta.value = text;
    ta.setAttribute('aria-hidden', 'true');
    ta.style.position = 'fixed';
    ta.style.left = '-9999px';
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand('copy'); done(); } catch (e) { /* nothing else to try */ }
    document.body.removeChild(ta);
  }

  function download() {
    var blob = new Blob([JSON.stringify(definition(), null, 2)], { type: 'application/json' });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = 'what-this-agent-can-do.json';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.setTimeout(function () { URL.revokeObjectURL(url); }, 0);
  }

  root.addEventListener('click', function (e) {
    var cap = e.target.closest ? e.target.closest('.cap') : null;
    if (cap) { toggle(cap.getAttribute('data-cap')); return; }
    var btn = e.target.closest ? e.target.closest('button') : null;
    if (!btn) return;
    if (btn.hasAttribute('data-ag-copy')) { copyOut(markdown(), btn); }
    else if (btn.hasAttribute('data-ag-download')) { download(); }
    else if (btn.hasAttribute('data-ag-clear')) {
      chosen = []; save(); renderChips(); renderList();
    }
  });

  /* The sequence prototype shows one family at a time. Same model, same chips —
     only which of them are on screen changes, which is the whole comparison. */
  if (mode === 'sequence') {
    var fams = Array.prototype.slice.call(root.querySelectorAll('.fam'));
    var at = 0;
    var nav = el('div', 'ag-nav');
    var back = el('button', 'buy buy-alt', 'Back');
    var next = el('button', 'buy', 'Next');
    var pos = el('span', 'ag-pos');
    back.type = next.type = 'button';
    nav.appendChild(back); nav.appendChild(pos); nav.appendChild(next);
    var pal = root.querySelector('.ag-palette');
    if (pal) pal.parentNode.insertBefore(nav, pal.nextSibling);
    var show = function () {
      fams.forEach(function (f, i) { f.hidden = i !== at; });
      pos.textContent = (at + 1) + ' of ' + fams.length;
      back.disabled = at === 0;
      next.disabled = at === fams.length - 1;
    };
    back.addEventListener('click', function () { if (at > 0) { at--; show(); } });
    next.addEventListener('click', function () { if (at < fams.length - 1) { at++; show(); } });
    show();
  }

  load();
  renderChips();
  renderList();
})();
