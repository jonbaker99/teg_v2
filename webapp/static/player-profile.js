/* Local profile behaviours; shared HTMX feedback and Plotly rendering stay in base. */
(function () {
    var profile = document.getElementById('player-profile');
    if (!profile) return;
    var originalFigures = new WeakMap();
    var phoneWidth = window.matchMedia('(max-width: 640px)');
    function initTrend(redraw) {
        var style = getComputedStyle(profile);
        var ink = style.getPropertyValue('--text-primary').trim();
        var muted = style.getPropertyValue('--text-secondary').trim();
        var rule = style.getPropertyValue('--table-cell-border').trim();
        var surface = style.getPropertyValue('--bg-card').trim();
        var narrow = phoneWidth.matches;
        profile.querySelectorAll('.pp-trend-chart[data-figure]').forEach(function (chart) {
            if (!originalFigures.has(chart)) originalFigures.set(chart, chart.dataset.figure);
            var figure = JSON.parse(originalFigures.get(chart));
            figure.data.forEach(function (trace) { trace.marker.color = muted; });
            var layout = figure.layout;
            layout.paper_bgcolor = 'transparent';
            layout.plot_bgcolor = 'transparent';
            layout.font.color = ink;
            layout.font.size = 11;
            layout.yaxis.gridcolor = rule;
            layout.yaxis.title.font = { size: 11, color: ink };
            layout.xaxis.tickangle = 0;
            layout.xaxis.tickmode = 'array';
            var labels = figure.data[0].x;
            layout.xaxis.tickvals = labels.filter(function (_, i) { return !narrow || i % 4 === 0 || i === labels.length - 1; });
            layout.xaxis.ticktext = layout.xaxis.tickvals.map(function (label) { return label.replace('TEG ', ''); });
            layout.xaxis.title = { text: 'TEG', font: { size: 11, color: ink } };
            (layout.shapes || []).forEach(function (shape) { if (shape.line) shape.line.color = muted; });
            layout.annotations = (layout.annotations || []).filter(function (annotation) {
                return !narrow || annotation.yanchor !== 'top';
            });
            layout.annotations.forEach(function (annotation) {
                annotation.font = { size: 11, color: muted };
                if (annotation.yanchor !== 'top') annotation.bgcolor = surface;
            });
            layout.margin.b = narrow ? 40 : 52;
            chart.dataset.figure = JSON.stringify(figure);
            if (redraw && window.Plotly && chart.classList.contains('js-plotly-plot')) {
                Plotly.react(chart, figure.data, layout, { responsive: true, displayModeBar: false });
            }
        });
    }
    function initRoundsChart(redraw) {
        var style = getComputedStyle(profile);
        var ink = style.getPropertyValue('--text-primary').trim();
        var muted = style.getPropertyValue('--text-secondary').trim();
        var rule = style.getPropertyValue('--table-cell-border').trim();
        var narrow = phoneWidth.matches;
        profile.querySelectorAll('.pp-rounds-chart[data-figure]').forEach(function (chart) {
            if (!originalFigures.has(chart)) originalFigures.set(chart, chart.dataset.figure);
            var figure = JSON.parse(originalFigures.get(chart));
            // Bar colour is the RdYlGn score scale (green = better round) --
            // meaningful data, unlike the trend chart's uniform bars, so it
            // is left alone; only axis/gridline/annotation chrome adapts.
            var layout = figure.layout;
            layout.paper_bgcolor = 'transparent';
            layout.plot_bgcolor = 'transparent';
            layout.font.color = ink;
            layout.font.size = 11;
            layout.yaxis.gridcolor = rule;
            layout.yaxis.title.font = { size: 11, color: ink };
            // _build_rounds_chart (player.py) tags the single "TEG" row
            // label with xref:'paper'; the per-TEG-group centred labels
            // never set xref -- same distinction the round chart's
            // add_round_annotations/applyMobileChartTreatment split relies
            // on elsewhere (yref:'paper' there), just on the other axis
            // here since this row label is a fixed left-margin caption, not
            // a per-category one.
            var groupLabels = (layout.annotations || []).filter(function (a) { return a.xref !== 'paper'; });
            var rowLabel = (layout.annotations || []).filter(function (a) { return a.xref === 'paper'; });
            // Same i%4-plus-last thinning heuristic initTrend uses for its
            // own one-per-TEG x ticks -- a dense history (David Mullin: 17
            // TEGs) packs these centred labels too close together at 320px
            // otherwise.
            var shown = groupLabels.filter(function (_, i) {
                return !narrow || i % 4 === 0 || i === groupLabels.length - 1;
            });
            layout.annotations = shown.concat(rowLabel);
            layout.annotations.forEach(function (a) { a.font = { size: 9, color: muted }; });
            chart.dataset.figure = JSON.stringify(figure);
            if (redraw && window.Plotly && chart.classList.contains('js-plotly-plot')) {
                Plotly.react(chart, figure.data, layout, { responsive: true, displayModeBar: false });
            }
        });
    }
    phoneWidth.addEventListener('change', function () { initTrend(true); initRoundsChart(true); });
    function initResults() {
        var results = profile.querySelector('[data-profile-results]');
        if (!results) return;
        var button = results.querySelector('[data-expand-profile-results]');
        if (!button) return;
        results.classList.add('is-collapsible');
        button.hidden = false;
    }
    initResults();
    initTrend();
    initRoundsChart();
    profile.addEventListener('change', function (event) {
        if (event.target.matches('[data-player-switch]')) window.location.assign(event.target.value);
    });
    profile.addEventListener('click', function (event) {
        var expand = event.target.closest('[data-expand-profile-results]');
        if (expand) {
            var results = expand.closest('[data-profile-results]');
            var open = results.classList.toggle('is-expanded');
            expand.setAttribute('aria-expanded', String(open));
            expand.textContent = open ? 'Show recent TEGs' : 'Show all ' + expand.dataset.resultCount + ' TEGs';
        }
        if (event.target.closest('[data-open-profile-records]')) profile.querySelector('[data-profile-tab="records"]').click();
        var chartPill = event.target.closest('.pp-chart-controls .chart-pill');
        if (chartPill) chartPill.closest('.pp-chart-controls').querySelectorAll('.chart-pill').forEach(function (pill) {
            pill.setAttribute('aria-pressed', String(pill === chartPill));
        });
    });
    document.addEventListener('htmx:afterSwap', function (event) {
        if (!event.detail.target || event.detail.target.id !== 'tab-content') return;
        initResults();
        initTrend();
        initRoundsChart();
        var trigger = event.detail.requestConfig && event.detail.requestConfig.elt;
        if (!trigger || !trigger.matches('[data-profile-tab]') || !profile.contains(trigger)) return;
        profile.querySelectorAll('[data-profile-tab]').forEach(function (button) {
            button.classList.toggle('pp-tab--active', button === trigger);
            button.setAttribute('aria-pressed', String(button === trigger));
        });
    });
})();
