// Local profile behaviours; shared HTMX feedback and Plotly rendering stay in base.
(function () {
    var profile = document.getElementById('player-profile');
    if (!profile) return;
    var originalFigures = new WeakMap();
    var phoneWidth = window.matchMedia('(max-width: 640px)');
    // Rounds tab chart: untouched on desktop, thinned labels on a phone.
    function initRoundsChart(redraw) {
        var narrow = phoneWidth.matches;
        profile.querySelectorAll('.pp-rounds-chart[data-figure]').forEach(function (chart) {
            if (!originalFigures.has(chart)) originalFigures.set(chart, chart.dataset.figure);
            var pristine = originalFigures.get(chart);

            // Restore the server figure when leaving phone width, since
            // dataset.figure may carry the phone-narrowed copy.
            if (!narrow) {
                chart.dataset.figure = pristine;
                if (redraw && window.Plotly && chart.classList.contains('js-plotly-plot')) {
                    var pristineFigure = JSON.parse(pristine);
                    Plotly.react(chart, pristineFigure.data, pristineFigure.layout, { responsive: true, displayModeBar: false });
                }
                return;
            }

            var style = getComputedStyle(profile);
            var ink = style.getPropertyValue('--text-primary').trim();
            var muted = style.getPropertyValue('--text-secondary').trim();
            var rule = style.getPropertyValue('--table-cell-border').trim();
            var figure = JSON.parse(pristine);
            // Bar colour is the RdYlGn score scale (green = better round) and
            // is meaningful data, so only the axis and annotation chrome adapts.
            var layout = figure.layout;
            layout.paper_bgcolor = 'transparent';
            layout.plot_bgcolor = 'transparent';
            layout.font.color = ink;
            layout.font.size = 11;
            layout.yaxis.gridcolor = rule;
            layout.yaxis.title.font = { size: 11, color: ink };
            // _build_rounds_chart (player.py) tags the single "TEG" row label
            // with xref:'paper'; the per-TEG centred labels never set xref.
            var groupLabels = (layout.annotations || []).filter(function (a) { return a.xref !== 'paper'; });
            var rowLabel = (layout.annotations || []).filter(function (a) { return a.xref === 'paper'; });
            // Keep every fourth TEG label plus the last, so a long history
            // does not pack the labels together at 320px.
            var shown = groupLabels.filter(function (_, i) {
                return i % 4 === 0 || i === groupLabels.length - 1;
            });
            layout.annotations = shown.concat(rowLabel);
            layout.annotations.forEach(function (a) { a.font = { size: 9, color: muted }; });
            chart.dataset.figure = JSON.stringify(figure);
            if (redraw && window.Plotly && chart.classList.contains('js-plotly-plot')) {
                Plotly.react(chart, figure.data, layout, { responsive: true, displayModeBar: false });
            }
        });
    }
    phoneWidth.addEventListener('change', function () { initRoundsChart(true); });
    initRoundsChart();
    profile.addEventListener('change', function (event) {
        if (event.target.matches('[data-player-switch]')) window.location.assign(event.target.value);
    });
    profile.addEventListener('click', function (event) {
        if (event.target.closest('[data-open-profile-records]')) profile.querySelector('[data-profile-tab="records"]').click();
    });
    document.addEventListener('htmx:afterSwap', function (event) {
        if (!event.detail.target || event.detail.target.id !== 'tab-content') return;
        initRoundsChart();
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
