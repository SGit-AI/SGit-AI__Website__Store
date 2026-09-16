/* vault-embed.js — the official SG/Vault interface, embedded read-only.
 *
 * VENDORED, NOT LINKED. Taken byte for byte from the estate's own component so
 * that a vault embeds the same way everywhere it embeds:
 *
 *   source     https://sgit.ai/assets/vault-ui-embed.js
 *   retrieved  15 September 2026
 *   sha256     6da5cf0a390dce2587d4b8fce6cd613ae4874761aa371c7bebb4308d4831f722
 *
 * It is copied rather than loaded across, for the same reason every other byte
 * on this site is served from this domain: a script pulled from another host at
 * page load is a second thing that can change under a reader without a release.
 * When the upstream moves, this file moves with it, in a commit that says so.
 *
 * THIS IS THE ONE PIECE OF CODE ON THIS SITE THAT OPENS A CONNECTION, and what
 * it does is worth reading rather than trusting:
 *
 *   * It builds an iframe AT RUNTIME. That is why no page here has <iframe> in
 *     its markup and why check_no_network needed a second check to see this at
 *     all — a rule that only reads the HTML cannot see a frame made by script.
 *   * The frame loads ONE host, pinned in a constant below, and the check holds
 *     it to that host.
 *   * THE KEY NEVER TOUCHES A URL. The frame is opened with no credential; it
 *     announces itself with {sg:'vault-embed-ready'}; only then is the key
 *     posted to it, with targetOrigin pinned to the vault origin. Replies are
 *     ignored unless e.origin matches. So the key is not in the address bar, not
 *     in history, not in a referrer, and not in the frame's storage.
 *   * The key it carries is a READ key. It opens the vault and cannot write to
 *     it, which was verified by cloning with one.
 *   * Nothing is sent about the reader. No analytics, no beacon, no cookie of
 *     ours, and this file contains no fetch, XHR, beacon or socket at all.
 *
 * Only a review page under /admin/reviews/ may load it, and only for a vault in
 * the frozen list of vaults ruled public. Both are checks, not conventions.
 */
(function () {
  'use strict';
  var ORIGIN = 'https://dev.vault.sgraph.ai';

  function mountAll() {
    var hosts = document.querySelectorAll('.sgv-uiembed');
    for (var i = 0; i < hosts.length; i++) mount(hosts[i]);
  }

  function mount(el) {
    var vaultId = el.getAttribute('data-vault');
    var readKey = el.getAttribute('data-readkey');
    var hasApp  = el.getAttribute('data-app') !== '0';
    if (!vaultId || !readKey) return;
    var cred = 'sgit_rk1_' + readKey + ':' + vaultId;

    var sections = [];
    if (hasApp) sections.push(section(el, cred, 'app', '▶ App Mode — the vault’s own app'));
    sections.push(section(el, cred, 'vault', '▤ Vault browser — FILES / SGIT / SETTINGS'));

    // One listener for the mount; route replies by which frame sent them.
    window.addEventListener('message', function (e) {
      if (e.origin !== ORIGIN) return;
      for (var i = 0; i < sections.length; i++) {
        var s = sections[i];
        if (!s.frame.contentWindow || e.source !== s.frame.contentWindow) continue;
        var d = e.data || {};
        if (d.sg === 'vault-embed-ready' && s.armed) {
          clearTimeout(s.fallbackT);
          e.source.postMessage({ sg: 'vault-open', key: cred, mode: s.mode }, ORIGIN);
          s.note.textContent = 'Handshake complete — key handed over postMessage, opening…';
        } else if (d.sg === 'vault-ready') {
          s.note.innerHTML = 'Opened <b>read-only</b> over the embed protocol — the key never appeared in a URL and was never written to the frame’s storage' +
            (d.fileCount ? '; ' + d.fileCount + ' files decrypted in the frame' : '') + '.';
          if (s.onReady) { s.onReady(); s.onReady = null; }
        } else if (d.sg === 'vault-error') {
          s.note.textContent = 'Vault open failed: ' + (d.message || 'unknown error');
          if (s.onReady) { s.onReady(); s.onReady = null; }
        }
        return;
      }
    });

    // Auto-open on load: the first surface now; the next when the previous is
    // ready (its fetches then hit the warm cache), with a grace timeout so one
    // slow surface never blocks the next.
    var chain = sections.slice();
    (function next() {
      var s = chain.shift();
      if (!s) return;
      var advanced = false;
      var advance = function () { if (!advanced) { advanced = true; next(); } };
      s.onReady = advance;
      setTimeout(advance, 9000);
      s.open();
    }());
  }

  // Build one surface: a label, its status line, its frame, and a retry control.
  function section(el, cred, mode, label) {
    var s = { mode: mode, armed: false, fallbackT: null, onReady: null };

    var h = document.createElement('div');
    h.className = 'sgv-uiembed-label';
    h.textContent = label;

    s.note = document.createElement('p');
    s.note.className = 'small dim'; s.note.style.margin = '.35rem 0 .5rem';
    s.note.textContent = 'Opening…';

    s.frame = document.createElement('iframe');
    s.frame.className = 'sgv-embed-frame sgv-embed-ui sgv-breakout';
    s.frame.title = 'The official SG/Vault UI (' + (mode === 'app' ? 'App Mode' : 'vault browser') + '), opened read-only';
    s.frame.style.display = 'none';

    el.appendChild(h); el.appendChild(s.note); el.appendChild(s.frame);

    s.open = function () {
      s.armed = true;
      s.frame.style.display = 'block';
      s.note.textContent = 'Handshaking with the vault UI…';
      var page = mode === 'vault' ? '/en-gb/vault/' : '/en-gb/app/';
      s.frame.src = ORIGIN + page + '?embed=1&parent=' + encodeURIComponent(location.origin);
      clearTimeout(s.fallbackT);
      s.fallbackT = setTimeout(function () {
        if (mode === 'app') {
          s.frame.src = ORIGIN + '/#' + encodeURIComponent(cred);
          s.note.textContent = 'Embed handshake timed out; fell back to the URL-fragment flow.';
        } else {
          s.note.innerHTML = 'Embed handshake timed out. ';
          var retry = document.createElement('button');
          retry.type = 'button'; retry.className = 'sgv-embed-load';
          retry.style.padding = '.2rem .7rem'; retry.style.fontSize = '.75rem';
          retry.textContent = '↻ retry';
          retry.addEventListener('click', function () { retry.remove(); s.open(); });
          s.note.appendChild(retry);
        }
      }, 12000);
    };
    return s;
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mountAll);
  else mountAll();
}());
