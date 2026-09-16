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

    var buy = byId('p-buy');
    if (buy) {
      buy.textContent = level.buyable
        ? 'Buy ' + level.short_name + ' →'
        : 'The payment link has not been issued yet';
      buy.setAttribute('aria-disabled', String(!level.buyable));
    }

    var claim = byId('p-claim');
    if (claim && level.claim) {
      // the arrow is part of the chip: it says the chip is a link to the
      // ledger entry, and dropping it on a switch made it look like a label
      claim.textContent = level.state_label + ' \u2197';
      claim.className = 'n-claim n-claim--' + level.state;
      claim.href = '/ledger/#claim-' + level.claim;
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
