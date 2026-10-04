/* TEGBot answer charts. The server (render_answer_html) validates the spec and
   leaves <div class="tegbot-chart" data-chart="...">; this draws it with the
   Plotly already loaded by base.html. All text goes in via textContent or
   Plotly, never innerHTML. Colours: dataviz reference palette, in order. */
(function () {
    var LIGHT = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#4a3aa7', '#e34948'];
    var DARK = ['#3987e5', '#d95926', '#199e70', '#c98500', '#d55181', '#008300', '#9085e9', '#e66767'];

    function el(tag, cls, text) {
        var n = document.createElement(tag);
        if (cls) n.className = cls;
        if (text != null) n.textContent = text;
        return n;
    }

    // Escape before adding our own <br>: Plotly reads a little HTML in tick text.
    function esc(t) {
        return String(t).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    function cssVar(node, name, fallback) {
        var v = getComputedStyle(node).getPropertyValue(name).trim();
        return v || fallback;
    }

    function dataTable(spec) {
        var d = el('details', 'tb-chart-data');
        d.appendChild(el('summary', null, 'Chart data'));
        var wrap = el('div', 'tb-chart-data-scroll');
        var t = el('table');
        var head = el('tr');
        head.appendChild(el('th', null, spec.x_label || ''));
        spec.series.forEach(function (s) { head.appendChild(el('th', null, s.name)); });
        t.appendChild(head);
        spec.x.forEach(function (x, i) {
            var r = el('tr');
            r.appendChild(el('td', null, String(x)));
            spec.series.forEach(function (s) {
                r.appendChild(el('td', null, s.values[i] == null ? '' : String(s.values[i])));
            });
            t.appendChild(r);
        });
        wrap.appendChild(t);
        d.appendChild(wrap);
        return d;
    }

    // Redraw when the chart crosses the narrow threshold (phone rotated, window
    // resized) so name wrapping follows. Debounced; one observer per chart.
    function watch(node) {
        if (node._tbWatching || !window.ResizeObserver) return;
        node._tbWatching = true;
        var timer = null;
        new ResizeObserver(function () {
            clearTimeout(timer);
            timer = setTimeout(function () {
                var w = node.clientWidth;
                if (!node.isConnected || !w || (w < 420) === node._tbNarrow) return;
                try { draw(node); } catch (e) { node.remove(); }
            }, 150);
        }).observe(node);
    }

    function draw(node) {
        var spec;
        try { spec = JSON.parse(node.getAttribute('data-chart')); } catch (e) { node.remove(); return; }
        var dark = document.documentElement.getAttribute('data-mode') === 'dark';
        var ink = cssVar(node, '--tb-ink', dark ? '#eeeeee' : '#111111');
        var green = cssVar(node, '--tb-green', dark ? '#5fb36f' : '#1f5c34');
        var line = cssVar(node, '--tb-grey-line', dark ? '#333333' : '#e3e3e1');
        var mono = cssVar(node, '--tb-mono', "'IBM Plex Mono', monospace");
        var palette = dark ? DARK : LIGHT;
        var multi = spec.series.length > 1;

        node.setAttribute('data-done', '1');
        node.setAttribute('role', 'img');
        node.setAttribute('aria-label', spec.title);
        node.textContent = '';
        node.appendChild(el('div', 'tb-chart-title', spec.title));
        var plot = el('div', 'tb-chart-plot');
        node.appendChild(plot);
        node.appendChild(dataTable(spec));

        var width = node.clientWidth || 360;
        var narrow = width < 420;
        node._tbNarrow = narrow;
        watch(node);
        var isBar = spec.type === 'bar';
        var tick = { size: 10, color: ink };
        var yAxisTitle = { text: spec.y_label || '', font: { size: 11, color: ink }, standoff: 8 };
        var base = { tickfont: tick, fixedrange: true, linecolor: line, zeroline: false, automargin: true };
        var layout = {
            paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
            font: { family: mono, size: 11, color: ink },
            showlegend: multi, dragmode: false, bargap: 0.3, barmode: 'group',
            legend: { orientation: 'h', x: 0, xanchor: 'left', y: -0.2, yanchor: 'top', font: { size: 10, color: ink } },
            hoverlabel: { font: { family: mono, size: 11 }, bgcolor: dark ? '#000' : '#fff', bordercolor: line }
        };
        var colour = function (i) { return multi ? palette[i % palette.length] : green; };
        var traces;

        if (isBar) {
            // Horizontal bars, best at the top. Sorted by the first series:
            // largest first, or smallest first when y_reverse says lower is better.
            var order = spec.x.map(function (_, i) { return i; });
            var first = spec.series[0].values;
            order.sort(function (a, b) {
                var va = first[a], vb = first[b];
                if (va == null || vb == null) return (va == null) - (vb == null);
                return spec.y_reverse ? va - vb : vb - va;
            });
            var cats = order.map(function (i) { return String(spec.x[i]); });
            // Names wrap onto two lines together, only when narrow and some label is long.
            var wrap = narrow && cats.some(function (c) { return c.length > 12; });
            var shown = cats.map(function (c) {
                var t = esc(c), k = c.indexOf(' ');
                return wrap && k > 0 ? esc(c.slice(0, k)) + '<br>' + esc(c.slice(k + 1)) : t;
            });
            traces = spec.series.map(function (s, i) {
                return {
                    name: s.name, type: 'bar', orientation: 'h', y: cats,
                    x: order.map(function (j) { return s.values[j]; }),
                    marker: { color: colour(i), line: { width: 0 } },
                    hovertemplate: '%{x}<extra>' + esc(s.name) + '</extra>'
                };
            });
            var rowH = multi ? spec.series.length * 15 + 14 : (wrap ? 40 : 30);
            layout.height = Math.min(760, 60 + cats.length * rowH + (multi ? 40 : 0));
            layout.margin = { l: 8, r: 16, t: 8, b: multi ? 70 : 40 };
            layout.hovermode = 'y unified';
            layout.yaxis = Object.assign({}, base, {
                type: 'category', autorange: 'reversed', showgrid: false,
                tickmode: 'array', tickvals: cats, ticktext: shown, tickangle: 0
            });
            layout.xaxis = Object.assign({}, base, { title: yAxisTitle, gridcolor: line, gridwidth: 1, rangemode: 'tozero' });
            // Legend order should match the top-to-bottom bar order within a group.
            layout.legend.traceorder = 'normal';
        } else {
            traces = spec.series.map(function (s, i) {
                return {
                    name: s.name, x: spec.x, y: s.values, type: 'scatter',
                    mode: spec.x.length <= 25 ? 'lines+markers' : 'lines', connectgaps: false,
                    line: { color: colour(i), width: 2 },
                    marker: { color: colour(i), size: 7, line: { color: dark ? '#1c1c1c' : '#f5f5f4', width: 1.5 } },
                    hovertemplate: '%{y}<extra>' + esc(s.name) + '</extra>'
                };
            });
            var textual = spec.x.some(function (v) { return typeof v === 'string'; });
            var xTitle = spec.x_label || '';
            var xaxis = Object.assign({}, base, { showgrid: false, tickangle: 0 });
            var maxTicks = narrow ? 6 : 12;
            if (textual) {
                var labels = spec.x.map(String);
                var shortL = labels, m = labels.map(function (l) { return /^(\D*?)\s*(\d+)$/.exec(l); });
                // "TEG 10" -> "10" when every label shares the same word before the number.
                if (m.every(function (r) { return r && r[1] === m[0][1]; })) {
                    shortL = m.map(function (r) { return r[2]; });
                    if (!xTitle) xTitle = m[0][1];
                }
                var step = Math.ceil(labels.length / maxTicks), vals = [], txt = [];
                labels.forEach(function (l, i) {
                    if (i % step === 0 || i === labels.length - 1 && step === 1) { vals.push(l); txt.push(esc(shortL[i])); }
                });
                Object.assign(xaxis, { type: 'category', tickmode: 'array', tickvals: vals, ticktext: txt });
            } else {
                xaxis.nticks = maxTicks;
            }
            xaxis.title = { text: xTitle, font: { size: 11, color: ink }, standoff: 8 };
            layout.height = multi ? 330 : 280;
            layout.margin = { l: 44, r: 12, t: 8, b: 40 };
            layout.hovermode = 'x unified';
            layout.xaxis = xaxis;
            layout.yaxis = Object.assign({}, base, { title: yAxisTitle, gridcolor: line, gridwidth: 1 });
            if (spec.y_reverse) layout.yaxis.autorange = 'reversed';
        }
        Plotly.newPlot(plot, traces, layout, { displayModeBar: false, responsive: true, scrollZoom: false });
    }

    function render(root) {
        if (!window.Plotly) return;
        (root || document).querySelectorAll('.tegbot-chart:not([data-done])').forEach(function (n) {
            // Charts inside a closed <details> measure zero width: wait for it to open.
            if (n.offsetWidth > 0) { try { draw(n); } catch (e) { n.remove(); } }
        });
    }

    document.addEventListener('DOMContentLoaded', function () { render(document); });
    document.addEventListener('htmx:afterSwap', function () { render(document); });
    document.addEventListener('htmx:afterSettle', function () { render(document); });
    document.addEventListener('toggle', function () { render(document); }, true);
    window.addEventListener('load', function () { render(document); });
})();
