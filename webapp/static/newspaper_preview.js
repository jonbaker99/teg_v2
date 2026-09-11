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

  function mastheadHtml() {
    var d = edition.dateline;
    return '<header class="m-masthead"><div class="m-mh-row">' +
      '<span class="m-wordmark">The TEG</span>' +
      '<span class="m-dateline">' + esc(d.teg) + " &middot; " + esc(d.venue) + " &middot; " + esc(d.year) + "</span>" +
      "</div><div class=\"m-mh-rule\"></div></header>";
  }
  function resultsHtml() {
    var items = edition.results.map(function (r) {
      var qual = r.value_qual ? ' <span class="m-r-qual">' + esc(r.value_qual) + "</span>" : "";
      return '<li class="m-r-item' + (r.lead ? " m-r-lead" : "") + '">' +
        '<span class="m-r-label">' + esc(r.label) + "</span>" +
        '<span class="m-r-vals"><span class="m-r-value">' + esc(r.value_name) + qual + "</span>" +
        (r.runner_up ? '<span class="m-r-runner">' + esc(r.runner_up) + "</span>" : "") +
        "</span></li>";
    }).join("");
    return '<div class="m-r5"><p class="m-r5-title">At a glance</p>' +
      '<ul class="m-r-list">' + items + "</ul></div>";
  }
  // Mirrors _totals_only/_round_only in teg_analysis/reporting/newspaper_edition.py:
  // standings rows carry each player's round score in brackets ("SN 156 (R4: 43)");
  // the cumulative table strips the bracket, the round-only table swaps in the
  // bracketed figure in place of the cumulative one. Round 1 rows have no bracket —
  // they already show the round score, since cumulative equals round score there.
  var ROUND_SCORE_BRACKET_RE = /\s*\(R\d+:[^)]*\)/g;
  var ROUND_ENTRY_RE = /([A-Z]{2}\s+[+-]?\d+)\s*\(R\d+:\s*([+-]?\d+)\)/g;

  function totalsOnly(row) {
    return row.replace(ROUND_SCORE_BRACKET_RE, "");
  }
  function roundOnly(row) {
    return row.replace(ROUND_ENTRY_RE, function (_, cumulative, roundScore) {
      return cumulative.split(/\s+/)[0] + " " + roundScore;
    });
  }
  function standingsTableHtml(rows) {
    return '<div class="table-scroll"><table class="stab">' +
      "<thead><tr><th>Rd</th><th>Trophy</th><th>Green Jacket</th></tr></thead>" +
      "<tbody>" + rows + "</tbody></table></div>";
  }

  function appendixHtml(open) {
    var cumulativeRows = edition.standings.map(function (s) {
      return "<tr><td>R" + s.round + "</td><td>" + esc(totalsOnly(s.trophy)) +
        "</td><td>" + esc(totalsOnly(s.jacket)) + "</td></tr>";
    }).join("");
    var roundRows = edition.standings.map(function (s) {
      return "<tr><td>R" + s.round + "</td><td>" + esc(roundOnly(s.trophy)) +
        "</td><td>" + esc(roundOnly(s.jacket)) + "</td></tr>";
    }).join("");
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
          '<div class="m-apx-sec">' + standingsTableHtml(cumulativeRows) + "</div>" +
          '<div class="m-apx-sec">' + standingsTableHtml(roundRows) + "</div>" +
          '<div class="m-apx-sec">' + recs + "</div>" +
        "</div>"
      : "";
    return '<section class="m-apx"><button type="button" class="m-apx-btn" data-apx="1" aria-expanded="' +
      (open ? "true" : "false") + '" aria-controls="apx-body">' +
      '<span class="m-apx-h">Standings &amp; records</span>' +
      '<span class="acc-sign" aria-hidden="true">' + (open ? "−" : "+") + "</span></button>" + body + "</section>";
  }

  function renderIndex() {
    var items = subs.map(function (a, i) {
      return '<button type="button" class="idx-item" data-open="' + (i + 1) + '">' +
        '<p class="kicker">' + esc(a.kicker) + "</p>" +
        '<h2 class="m-hl">' + esc(a.headline) + "</h2>" +
        '<span class="idx-foot"><span class="m-meta">' + readTime(a.words) + "</span>" +
        '<span class="chev" aria-hidden="true">Read &rarr;</span></span></button>';
    }).join("");

    return '<div class="scroller" id="scroller">' +
      mastheadHtml() + resultsHtml() +
      '<button type="button" class="idx-lead" data-open="0">' +
        '<p class="kicker">' + esc(lead.kicker) + "</p>" +
        '<h1 class="m-hl">' + esc(lead.headline) + "</h1>" +
        (lead.standfirst ? '<p class="m-sf">' + esc(lead.standfirst) + "</p>" : "") +
        '<span class="lead-cta"><span class="m-meta">' + readTime(lead.words) + "</span>" +
        '<span class="chev" aria-hidden="true">Read the report &rarr;</span></span>' +
      "</button>" +
      '<nav class="idx-list" aria-label="In this edition">' +
        '<p class="idx-h">Also in this edition</p>' + items +
      "</nav>" +
      appendixHtml(state.apxOpen) +
    "</div>";
  }

  function renderArticle(i) {
    var a = all[i], prev = all[i - 1], next = all[i + 1];
    function navBtn(art, j, label) {
      if (!art) return '<button type="button" disabled><span class="an-lab">' + label + "</span></button>";
      return '<button type="button" data-open="' + j + '"><span class="an-lab">' + label + "</span>" +
        '<span class="an-hl">' + esc(art.headline) + "</span></button>";
    }
    return '<div class="scroller" id="scroller">' +
      '<div class="topbar"><button type="button" data-index="1">&larr; Front page</button>' +
        '<span class="tb-title">' + esc(edition.dateline.teg) + "</span></div>" +
      '<article class="article">' +
        '<p class="kicker">' + esc(a.kicker) + "</p>" +
        '<h1 class="m-hl" id="screen-title" tabindex="-1">' + esc(a.headline) + "</h1>" +
        (a.standfirst ? '<p class="m-sf">' + esc(a.standfirst) + "</p>" : "") +
        '<div class="m-body">' + paragraphsHtml(a.paragraphs) + "</div>" +
      "</article>" +
      '<nav class="artnav" aria-label="Other articles">' +
        navBtn(prev, i - 1, "Previous") + navBtn(next, i + 1, "Next") + "</nav>" +
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
    bindScreen();
    restoreScroll();
  }

  fromHash();
  render();
})();
