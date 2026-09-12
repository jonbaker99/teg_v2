/* Newspaper report layout — mobile pattern A (index first).
 *
 * Ported from webapp/report_layout_prototypes/mobile.html, pattern A only
 * (B/C were not shipped — see that folder's README.md "Decisions worth not
 * relitigating"). The prototype renders three switchable patterns for three
 * hardcoded TEGs from an inlined array; this only ever renders the one
 * edition the server embedded for this page, and there is no pattern switch.
 *
 * Coexists with the server-rendered desktop stage (#desktop-stage, plain
 * HTML, no JS) via a CSS breakpoint in newspaper_preview.css: only one of
 * #desktop-stage/#mobile-stage is ever visible. This script always runs
 * (cheap — string building, no measurement) so the correct stage is ready
 * the moment a resize crosses the breakpoint.
 *
 * Hash routing so the phone's Back gesture works: "" is the index, "#story/N"
 * is article N (0 = lead). Any screen can be entered cold from its hash.
 */
(function () {
  "use strict";

  var dataEl = document.getElementById("edition-data");
  var mount = document.getElementById("mobile-stage");
  if (!dataEl || !mount) return;

  var edition = JSON.parse(dataEl.textContent);
  var lead = edition.articles.filter(function (a) { return a.is_lead; })[0];
  var subs = edition.articles.filter(function (a) { return !a.is_lead; });
  var all = [lead].concat(subs);

  var state = { view: null, apxOpen: false };
  var indexScroll = 0;
  var historyAvailable = true;

  function esc(s) {
    return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }
  function paragraphsHtml(ps) {
    return ps.map(function (p) {
      return "<p>" + esc(p).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>") + "</p>";
    }).join("");
  }
  function readTime(words) { return Math.max(1, Math.ceil(words / 200)) + " min read"; }

  function editionTitle() {
    // "TEG 16" for a tournament edition, "TEG 16 · Round 2" for a round one —
    // mirrors newspaper_edition._masthead_html / _appendix_title server-side.
    var d = edition.dateline;
    return d.round ? esc(d.teg) + " · Round " + d.round : esc(d.teg);
  }
  function mastheadHtml() {
    var d = edition.dateline;
    return '<header class="m-masthead"><div class="m-mh-row">' +
      '<span class="m-wordmark">' + editionTitle() + "</span>" +
      '<span class="m-dateline">' + esc(d.venue) + " &middot; " + esc(d.year) + "</span>" +
      "</div><div class=\"m-mh-rule\"></div></header>";
  }
  function resultsHtml() {
    // Slim strip, no runner-up (2026-09-12) — see newspaper_preview.css's
    // .m-strip comment for why. r.runner_up still arrives in the edition
    // data; this simply doesn't render it.
    var items = edition.results.map(function (r) {
      var qual = r.value_qual ? ' <span class="m-strip-qual">' + esc(r.value_qual) + "</span>" : "";
      return '<div class="m-strip-item">' +
        '<span class="m-strip-label">' + esc(r.label) + "</span>" +
        '<span class="m-strip-value"><strong>' + esc(r.value_name) + "</strong>" + qual + "</span>" +
        "</div>";
    }).join("");
    return '<div class="m-strip"><p class="m-strip-h">At a glance</p>' +
      '<div class="m-strip-list">' + items + "</div></div>";
  }
  function appendixHtml(open) {
    // Standings tables dropped 2026-09-11: they duplicate the round-by-round
    // and leaderboard views shown better elsewhere in the app. Records only.
    var by = {}, order = [];
    edition.records.forEach(function (r) {
      if (!by[r.category]) { by[r.category] = []; order.push(r.category); }
      by[r.category].push(r.text);
    });
    var recs = order.map(function (c) {
      return '<div class="recs-group"><p class="recs-cat">' + esc(c) + '</p><ul class="recs">' +
        by[c].map(function (t) { return "<li>" + esc(t) + "</li>"; }).join("") + "</ul></div>";
    }).join("");
    var body = open
      ? '<div class="m-apx-body" id="apx-body">' +
          '<h3 class="m-apx-hl">Notable achievements: ' + editionTitle() + '</h3>' +
          '<div class="m-apx-sec">' + recs + "</div></div>"
      : "";
    return '<section class="m-apx"><button type="button" class="m-apx-btn" data-apx="1" aria-expanded="' +
      (open ? "true" : "false") + '" aria-controls="apx-body">' +
      '<span class="m-apx-h">Records &amp; Personal Bests</span>' +
      '<span class="acc-sign" aria-hidden="true">' + (open ? "−" : "+") + "</span></button>" + body + "</section>";
  }

  function renderIndex() {
    var items = subs.map(function (a, i) {
      return '<button type="button" class="idx-item" data-open="' + (i + 1) + '">' +
        '<p class="kicker">' + esc(a.descriptor || a.kicker) + "</p>" +
        '<h2 class="m-hl">' + esc(a.headline) + "</h2>" +
        '<span class="idx-foot"><span class="m-meta">' + readTime(a.words) + "</span>" +
        '<span class="chev" aria-hidden="true">Read &rarr;</span></span></button>';
    }).join("");

    return '<div class="scroller" id="scroller">' +
      mastheadHtml() +
      '<button type="button" class="idx-lead" data-open="0">' +
        '<p class="kicker">' + esc(lead.descriptor || lead.kicker) + "</p>" +
        '<h1 class="m-hl">' + esc(lead.headline) + "</h1>" +
        (lead.standfirst ? '<p class="m-sf">' + esc(lead.standfirst) + "</p>" : "") +
        '<span class="lead-cta"><span class="m-meta">' + readTime(lead.words) + "</span>" +
        '<span class="chev" aria-hidden="true">Read the report &rarr;</span></span>' +
      "</button>" +
      resultsHtml() +
      '<nav class="idx-list" aria-label="In this edition">' +
        '<p class="idx-h">Also in this edition</p>' + items +
      "</nav>" +
      appendixHtml(state.apxOpen) +
    "</div>";
  }

  var CHEVRON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" ' +
    'stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"></polyline></svg>';

  function renderArticle(i) {
    var a = all[i], prev = all[i - 1], next = all[i + 1];
    // Previous/Next omitted entirely when absent rather than shown disabled
    // (2026-09-12) — a clean minimalist link list has no ghost rows.
    function navLine(art, j, label) {
      if (!art) return "";
      return '<button type="button" class="an-line" data-open="' + j + '">' +
        '<span class="an-dir">' + label + '</span><span class="an-hl">' + esc(art.headline) + "</span></button>";
    }
    var frontLine = '<button type="button" class="an-line an-front" data-index="1">' +
      '<span class="an-dir">&larr;</span><span class="an-hl">Report front page</span></button>';
    return '<div class="scroller" id="scroller">' +
      '<div class="topbar"><button type="button" data-index="1">' + CHEVRON + "Report front page</button>" +
        '<span class="tb-title">' + editionTitle() + "</span></div>" +
      '<div class="kicker-line"><p class="kicker">' + esc(a.descriptor || a.kicker) + "</p></div>" +
      '<article class="article">' +
        '<h1 class="m-hl" id="screen-title" tabindex="-1">' + esc(a.headline) + "</h1>" +
        (a.standfirst ? '<p class="m-sf">' + esc(a.standfirst) + "</p>" : "") +
        '<div class="m-body">' + paragraphsHtml(a.paragraphs) + "</div>" +
      "</article>" +
      '<nav class="artnav" aria-label="Other articles">' +
        navLine(prev, i - 1, "Previous") + navLine(next, i + 1, "Next") + frontLine + "</nav>" +
    "</div>";
  }

  /* ---- routing --------------------------------------------------------- */

  function toHash() {
    return state.view === null ? "" : "#story/" + state.view;
  }
  function fromHash() {
    var m = /^#story\/(\d+)$/.exec(location.hash || "");
    state.view = m ? Math.min(parseInt(m[1], 10) || 0, all.length - 1) : null;
  }
  function writeHistory(h, replace) {
    try {
      if (replace) history.replaceState(null, "", h || location.pathname + location.search);
      else history.pushState(null, "", h || location.pathname + location.search);
    } catch (err) {
      historyAvailable = false;
    }
  }
  function go(patch, replace) {
    Object.assign(state, patch);
    var h = toHash();
    if ((location.hash || "") === h) { render(); return; }
    writeHistory(h, replace);
    render();
  }
  window.addEventListener("popstate", function () {
    fromHash();
    render();
  });

  function scrollHost() {
    var s = document.getElementById("scroller");
    if (s && s.scrollHeight > s.clientHeight + 1) return s;
    return document.scrollingElement || document.documentElement;
  }
  function restoreScroll() {
    var host = scrollHost();
    if (state.view === null) {
      host.scrollTop = indexScroll;
      (host === document.scrollingElement ? window : host)
        .addEventListener("scroll", function () { indexScroll = host.scrollTop; }, { passive: true });
    } else {
      host.scrollTop = 0;
      var h = document.getElementById("screen-title");
      if (h) h.focus({ preventScroll: true });
    }
  }

  function bindScreen() {
    mount.querySelectorAll("[data-open]").forEach(function (b) {
      b.addEventListener("click", function () {
        go({ view: parseInt(b.getAttribute("data-open"), 10) });
      });
    });
    mount.querySelectorAll("[data-index]").forEach(function (b) {
      b.addEventListener("click", function () { go({ view: null }); });
    });
    mount.querySelectorAll("[data-apx]").forEach(function (b) {
      b.addEventListener("click", function () { state.apxOpen = !state.apxOpen; render(); });
    });
  }

  document.addEventListener("keydown", function (ev) {
    if (ev.metaKey || ev.ctrlKey || ev.altKey) return;
    if (state.view !== null && ev.key === "Escape") {
      ev.preventDefault();
      if (historyAvailable) history.back(); else go({ view: null }, true);
    }
  });

  function render() {
    mount.innerHTML = state.view === null ? renderIndex() : renderArticle(state.view);
    document.body.classList.toggle("np-reading", state.view !== null);
    bindScreen();
    restoreScroll();
  }

  fromHash();
  render();
})();
