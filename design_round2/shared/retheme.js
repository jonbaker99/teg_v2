/* design_round2 prototype runtime.
   1. Re-renders every Plotly chart from its pristine data-figure JSON with the
      styling's --chart-* / --font-data tokens applied, so charts follow the
      theme and the light/dark mode.
   2. Replaces the server-driven mode toggle (cookie + reload) with a client
      flip of html[data-mode], then re-renders charts.
   3. If the styling defines rank-tier tokens (--table-tier1-bg …), applies
      tier classes to leaderboard rows so Theme C colour-coding lights up. */

(function () {
    'use strict';

    function cssVar(name) {
        return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    }

    function palette() {
        var out = [];
        for (var i = 1; i <= 8; i++) {
            var c = cssVar('--chart-' + i);
            if (c) out.push(c);
        }
        return out.length ? out : ['#636EFA', '#EF553B', '#00CC96', '#AB63FA', '#FFA15A'];
    }

    function themedFig(el) {
        var fig = JSON.parse(el.dataset.figure);
        var pal = palette();
        var grid = cssVar('--chart-grid') || 'rgba(0,0,0,0.08)';
        var axisText = cssVar('--chart-axis-text') || cssVar('--text-muted') || '#999';
        var muted = cssVar('--text-muted') || '#999';
        var markerFill = cssVar('--bg-card') || cssVar('--bg-page') || '#fff';
        var dataFont = (cssVar('--font-data') || "'Roboto Mono'") + ', monospace';

        var colorMap = {}; // old trace colour -> new palette colour

        (fig.data || []).forEach(function (tr, i) {
            var next = pal[i % pal.length];
            var old = (tr.line && tr.line.color) ||
                (tr.marker && typeof tr.marker.color === 'string' && tr.marker.color !== 'white'
                    ? tr.marker.color : null);
            if (old) colorMap[String(old).toLowerCase()] = next;
            if (tr.line && tr.line.color) tr.line.color = next;
            if (tr.marker) {
                if (typeof tr.marker.color === 'string') {
                    tr.marker.color = tr.marker.color === 'white' ? markerFill : next;
                }
                if (tr.marker.line && typeof tr.marker.line.color === 'string') {
                    var mapped = colorMap[String(tr.marker.line.color).toLowerCase()];
                    if (mapped) tr.marker.line.color = mapped;
                }
            }
        });

        var lay = fig.layout = fig.layout || {};
        lay.paper_bgcolor = 'rgba(0,0,0,0)';
        lay.plot_bgcolor = 'rgba(0,0,0,0)';
        lay.font = Object.assign({}, lay.font, { family: dataFont, color: axisText });
        ['xaxis', 'yaxis'].forEach(function (ax) {
            if (!lay[ax]) return;
            if (lay[ax].gridcolor) lay[ax].gridcolor = grid;
            lay[ax].tickfont = Object.assign({}, lay[ax].tickfont, { color: axisText });
            if (lay[ax].title) {
                lay[ax].title.font = Object.assign({}, lay[ax].title.font, { color: axisText });
            }
        });
        if (lay.legend) {
            lay.legend.font = Object.assign({}, lay.legend.font, { color: axisText });
        }
        (lay.annotations || []).forEach(function (an) {
            if (!an.font) an.font = {};
            var mapped = an.font.color && colorMap[String(an.font.color).toLowerCase()];
            an.font.color = mapped || muted;
        });
        (lay.shapes || []).forEach(function (sh) {
            if (sh.line && sh.line.color) {
                // near-transparent structural lines -> grid colour; emphasis lines -> muted
                sh.line.color = /rgba\(0,\s*0,\s*0/.test(sh.line.color) ? grid : muted;
            }
        });
        return fig;
    }

    function renderThemed(root) {
        (root || document).querySelectorAll('.chart-container[data-figure]').forEach(function (el) {
            try {
                var fig = themedFig(el);
                Plotly.purge(el);
                Plotly.newPlot(el, fig.data, fig.layout, { responsive: true, displayModeBar: false });
            } catch (e) {
                console.error('retheme failed for chart', e);
            }
        });
    }

    /* Rank-tier colour coding — only active when the styling defines the
       tier tokens (Theme C). Rows keep their classes across mode flips;
       the colours re-point via the CSS variables. */
    function applyTiers() {
        if (!cssVar('--table-tier1-bg')) return;
        document.querySelectorAll('table.leaderboard-table tbody').forEach(function (tbody) {
            var rows = Array.prototype.slice.call(tbody.querySelectorAll('tr'));
            var ranked = rows.map(function (tr) {
                var cell = tr.querySelector('td.col-rank') || tr.querySelector('td');
                return { tr: tr, rank: parseInt(cell ? cell.textContent : '', 10) };
            }).filter(function (r) { return !isNaN(r.rank); });
            if (!ranked.length) return;
            var maxRank = Math.max.apply(null, ranked.map(function (r) { return r.rank; }));
            ranked.forEach(function (r) {
                r.tr.classList.remove('top-rank');
                if (r.rank === 1) r.tr.classList.add('tier-1');
                else if (r.rank <= 3 && r.rank !== maxRank) r.tr.classList.add('tier-2');
                else if (r.rank === maxRank) r.tr.classList.add('tier-last');
                else r.tr.classList.add('tier-mid');
            });
        });
    }

    /* Client-side light/dark toggle (the app version sets a cookie and
       reloads; a static prototype flips the attribute directly). */
    window.tegToggleMode = function () {
        var html = document.documentElement;
        var next = html.getAttribute('data-mode') === 'dark' ? 'light' : 'dark';
        html.setAttribute('data-mode', next);
        try { localStorage.setItem('dr2-mode', next); } catch (e) { /* file:// */ }
        renderThemed(document);
    };

    document.addEventListener('DOMContentLoaded', function () {
        var toggle = document.querySelector('.mode-toggle');
        if (toggle) toggle.setAttribute('onclick', 'tegToggleMode()');
        try {
            var saved = localStorage.getItem('dr2-mode');
            if (saved && !document.documentElement.hasAttribute('data-mode-fixed')) {
                document.documentElement.setAttribute('data-mode', saved);
            }
        } catch (e) { /* file:// */ }
        applyTiers();
        // The page's own renderCharts listener runs first; this re-render
        // replaces those plots with token-themed versions.
        renderThemed(document);
    });
})();
