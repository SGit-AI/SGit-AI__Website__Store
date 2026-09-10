/* site.js — the whole of this site's non-lab JavaScript: one nav toggle.
   No analytics, no cookies, no third-party anything. */
(function () {
  var nav = document.querySelector('nav.site');
  var btn = nav && nav.querySelector('.nav-toggle');
  if (!btn) return;
  btn.addEventListener('click', function () {
    var open = nav.classList.toggle('open');
    btn.setAttribute('aria-expanded', open ? 'true' : 'false');
  });
})();
