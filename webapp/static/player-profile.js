// Local profile behaviours; shared HTMX feedback and Plotly rendering stay in base.
(function () {
    var profile = document.getElementById('player-profile');
    if (!profile) return;
    var originalFigures = new WeakMap();
    var phoneWidth = window.matchMedia('(max-width: 640px)');
    // Server figures carry two sentinel bar colours; swap them for the theme's.
    var NEUTRAL = '#b5b5b5';
    var JACKET = '#228b22';
    function themed(pristine, narrow, isRounds) {
        var style = getComputedStyle(profile);
        var ink = style.getPropertyValue('--text-primary').trim();
        var muted = style.getPropertyValue('--text-secondary').trim();
        var grey = style.getPropertyValue('--text-muted').trim();
        var accent = style.getPropertyValue('--accent').trim();
        var rule = style.getPropertyValue('--table-cell-border').trim();
        var figure = JSON.parse(pristine);
        function recolour(c) {
            if (c === NEUTRAL) return grey;
            if (c === JACKET) return accent;
            return c;
        }
        figure.data.forEach(function (trace) {
            if (!trace.marker) return;
            trace.marker.color = Array.isArray(trace.marker.color)
                ? trace.marker.color.map(recolour) : recolour(trace.marker.color);
        });
        var layout = figure.layout;
        layout.paper_bgcolor = 'transparent';
        layout.plot_bgcolor = 'transparent';
        layout.font = layout.font || {};
        layout.font.color = ink;
        layout.font.size = 11;
        layout.yaxis.gridcolor = rule;
        layout.yaxis.title = layout.yaxis.title || {};
        layout.yaxis.title.font = { size: 11, color: ink };
        if (layout.xaxis && layout.xaxis.title) layout.xaxis.title.font = { size: 11, color: ink };
        (layout.annotations || []).forEach(function (a) { a.font = { size: 9, color: muted }; });
        if (isRounds && narrow) {
            // The per-TEG centred labels never set xref; the single "TEG" row
            // label sets xref:'paper' (_build_rounds_chart in player.py).
            var groupLabels = (layout.annotations || []).filter(function (a) { return a.xref !== 'paper'; });
            var rowLabel = (layout.annotations || []).filter(function (a) { return a.xref === 'paper'; });
            // Keep every fourth TEG label plus the last, so a long history
            // does not pack the labels together at 320px.
            var shown = groupLabels.filter(function (_, i) { return i % 4 === 0 || i === groupLabels.length - 1; });
            layout.annotations = shown.concat(rowLabel);
        }
        return figure;
    }
    function initCharts(redraw) {
        var narrow = phoneWidth.matches;
        profile.querySelectorAll('.pp-chart[data-figure]').forEach(function (chart) {
            if (!originalFigures.has(chart)) originalFigures.set(chart, chart.dataset.figure);
            var figure = themed(originalFigures.get(chart), narrow, chart.classList.contains('pp-rounds-chart'));
            chart.dataset.figure = JSON.stringify(figure);
            if (redraw && window.Plotly && chart.classList.contains('js-plotly-plot')) {
                Plotly.react(chart, figure.data, figure.layout, { responsive: true, displayModeBar: false });
            }
        });
    }
    phoneWidth.addEventListener('change', function () { initCharts(true); });
    initCharts();
    profile.addEventListener('change', function (event) {
        if (event.target.matches('[data-player-switch]')) window.location.assign(event.target.value);
    });
    profile.addEventListener('click', function (event) {
        if (event.target.closest('[data-open-profile-records]')) profile.querySelector('[data-profile-tab="records"]').click();
    });
    document.addEventListener('htmx:afterSwap', function (event) {
        if (!event.detail.target || event.detail.target.id !== 'tab-content') return;
        initCharts();
        var trigger = event.detail.requestConfig && event.detail.requestConfig.elt;
        if (!trigger || !trigger.matches('[data-profile-tab]') || !profile.contains(trigger)) return;
        // Commit profile-tab state only after the requested partial swaps.
        // ui-polish.js follows the same successful-response contract and
        // owns the canonical URL/history entry.
        profile.querySelectorAll('[data-profile-tab]').forEach(function (button) {
            button.classList.toggle('tab-underline--active', button === trigger);
            button.setAttribute('aria-pressed', String(button === trigger));
        });
    });
})();
