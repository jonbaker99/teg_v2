/* Native navigation plus the shared public read-request state contract. */
(function () {
    var hamburger = document.querySelector('.nav-hamburger--tablet');
    var links = document.querySelector('.nav-links');
    var menus = Array.from(document.querySelectorAll('.nav-dropdown'));
    function closeMenus() {
        menus.forEach(function (menu) {
            menu.classList.remove('open');
            menu.querySelector('button').setAttribute('aria-expanded', 'false');
        });
    }
    if (hamburger && links) {
        hamburger.addEventListener('click', function () {
            var open = links.classList.toggle('open');
            hamburger.setAttribute('aria-expanded', String(open));
            hamburger.setAttribute('aria-label', open ? 'Close navigation' : 'Open navigation');
            if (!open) closeMenus();
        });
        document.addEventListener('keydown', function (event) {
            if (event.key !== 'Escape') return;
            var active = document.activeElement.closest('.nav-dropdown');
            if (active) active.querySelector('button').focus();
            else if (links.classList.contains('open')) hamburger.focus();
            closeMenus();
            links.classList.remove('open');
            hamburger.setAttribute('aria-expanded', 'false');
            hamburger.setAttribute('aria-label', 'Open navigation');
        });
        document.addEventListener('click', function (event) {
            if (event.target.closest('.nav')) return;
            closeMenus();
            links.classList.remove('open');
            hamburger.setAttribute('aria-expanded', 'false');
            hamburger.setAttribute('aria-label', 'Open navigation');
        });
    }
    menus.forEach(function (menu) {
        var button = menu.querySelector('button');
        button.addEventListener('click', function () {
            var open = !menu.classList.contains('open');
            closeMenus();
            menu.classList.toggle('open', open);
            button.setAttribute('aria-expanded', String(open));
        });
    });

    var exploreSheet = document.getElementById('mobile-explore-sheet');
    var exploreTriggers = Array.from(document.querySelectorAll('[data-explore-trigger]'));
    var exploreClose = exploreSheet && exploreSheet.querySelector('[data-explore-close]');
    var exploreInvoker = null;
    var phoneViewport = window.matchMedia('(max-width: 640px)');
    function setExploreExpanded(open) {
        exploreTriggers.forEach(function (trigger) {
            trigger.setAttribute('aria-expanded', String(open));
        });
    }
    function openExplore(trigger) {
        if (!exploreSheet || !phoneViewport.matches || exploreSheet.open) return;
        exploreInvoker = trigger;
        exploreSheet.showModal();
        document.body.classList.add('mobile-explore-open');
        setExploreExpanded(true);
        if (exploreClose) exploreClose.focus({ preventScroll: true });
    }
    function closeExplore() {
        if (exploreSheet && exploreSheet.open) exploreSheet.close();
    }
    exploreTriggers.forEach(function (trigger) {
        trigger.addEventListener('click', function () { openExplore(trigger); });
    });
    if (exploreClose) exploreClose.addEventListener('click', closeExplore);
    if (exploreSheet) {
        exploreSheet.addEventListener('click', function (event) {
            if (event.target === exploreSheet) closeExplore();
        });
        exploreSheet.addEventListener('close', function () {
            document.body.classList.remove('mobile-explore-open');
            setExploreExpanded(false);
            if (exploreInvoker) exploreInvoker.focus({ preventScroll: true });
            exploreInvoker = null;
        });
    }
    function closeExploreAbovePhone() {
        if (!phoneViewport.matches) closeExplore();
    }
    phoneViewport.addEventListener('change', closeExploreAbovePhone);

    var root = document.body;
    if (!root || !root.hasAttribute('data-public-state-keys')) return;

    var keys = root.getAttribute('data-public-state-keys').split(',').map(function (key) {
        return key.trim();
    }).filter(Boolean);
    var feedback = document.getElementById('request-feedback');
    var message = feedback.querySelector('[data-request-message]');
    var retryButton = feedback.querySelector('[data-request-retry]');
    var dismissButton = feedback.querySelector('[data-request-dismiss]');
    var requests = new WeakMap();
    var targetCounts = new WeakMap();
    var latestByTarget = new WeakMap();
    var confirmed = Object.create(null);
    var failedRequest = null;
    var retryPending = null;
    var pendingCount = 0;

    function simpleValue(value) {
        if (Array.isArray(value)) return value.length ? String(value[value.length - 1]) : '';
        if (value === undefined || value === null) return '';
        return String(value);
    }

    function copyParameters(parameters) {
        // HTMX's programmatic-request path calls values.hasOwnProperty(), so
        // Retry must receive an ordinary object rather than a null-prototype
        // map even though either shape is fine for our own reads.
        var values = {};
        if (!parameters) return values;
        if (typeof parameters.forEach === 'function') {
            parameters.forEach(function (value, key) { values[key] = simpleValue(value); });
            return values;
        }
        Object.keys(parameters).forEach(function (key) { values[key] = simpleValue(parameters[key]); });
        return values;
    }

    function controlValue(control) {
        if (!control) return '';
        if (control.type === 'checkbox') return control.checked ? simpleValue(control.value || 'true') : 'false';
        if (control.type === 'radio') return control.checked ? simpleValue(control.value) : '';
        return simpleValue(control.value);
    }

    function elementsInScope(scope, selector) {
        var elements = Array.from(scope.querySelectorAll(selector));
        if (scope.matches && scope.matches(selector)) elements.unshift(scope);
        return elements;
    }

    function collectControlState(scope, state) {
        keys.forEach(function (key) {
            var controls = elementsInScope(scope, '[name="' + CSS.escape(key) + '"]');
            var control = controls.find(function (candidate) {
                return candidate.type !== 'radio' || candidate.checked;
            });
            if (control) state[key] = controlValue(control);
        });
    }

    function collectAnnotatedState(scope, state, missingOnly) {
        elementsInScope(scope, '[data-public-state-key][data-public-state-value]').forEach(function (control) {
            var key = control.dataset.publicStateKey;
            if (keys.indexOf(key) < 0 || (missingOnly && state[key] !== undefined)) return;
            var active = control.classList.contains('tab-underline--active') ||
                control.classList.contains('pill--active') ||
                control.getAttribute('aria-pressed') === 'true';
            if (active) state[key] = simpleValue(control.dataset.publicStateValue);
        });
    }

    function collectResponseState(snapshot, responseText) {
        if (!responseText) return;
        var template = document.createElement('template');
        template.innerHTML = responseText;
        collectControlState(template.content, snapshot.responseValues);
        collectAnnotatedState(template.content, snapshot.responseValues, false);
    }

    function rememberControls() {
        document.querySelectorAll('input[name], select[name], textarea[name]').forEach(function (control) {
            var value = keys.indexOf(control.name) >= 0 && confirmed[control.name] !== undefined
                ? confirmed[control.name]
                : controlValue(control);
            control.dataset.publicConfirmedValue = simpleValue(value);
        });
    }

    function applyConfirmedControls(snapshot) {
        keys.forEach(function (key) {
            if (confirmed[key] === undefined) return;
            document.querySelectorAll('[name="' + CSS.escape(key) + '"]').forEach(function (control) {
                var value = simpleValue(confirmed[key]);
                if (control.type === 'checkbox' || control.type === 'radio') {
                    control.checked = simpleValue(control.value || 'true') === value;
                } else {
                    var continuous = control.matches('input[type="text"], input[type="number"], input[type="range"]');
                    var requestOwnsValue = Object.prototype.hasOwnProperty.call(snapshot.values, key);
                    if (continuous && !snapshot.retrying && (
                        !requestOwnsValue || controlValue(control) !== simpleValue(snapshot.values[key])
                    )) return;
                    control.value = value;
                }
            });
        });
    }

    function restoreControls() {
        document.querySelectorAll('[data-public-confirmed-value]').forEach(function (control) {
            var value = control.dataset.publicConfirmedValue;
            if (control.type === 'checkbox' || control.type === 'radio') {
                control.checked = simpleValue(control.value || 'true') === value;
            } else {
                control.value = value;
            }
        });
        syncSelections();
        document.dispatchEvent(new CustomEvent('public-state:rollback', { detail: { state: Object.assign({}, confirmed) } }));
    }

    function syncSelections() {
        document.querySelectorAll('[data-public-state-key]').forEach(function (control) {
            var values = (control.dataset.publicStateValues || control.dataset.publicStateValue || '').split(',');
            var active = values.indexOf(simpleValue(confirmed[control.dataset.publicStateKey])) >= 0;
            if (control.classList.contains('tab-underline')) {
                control.classList.toggle('tab-underline--active', active);
                control.setAttribute('aria-pressed', String(active));
            }
            if (control.classList.contains('pill')) control.classList.toggle('pill--active', active);
            if (control.classList.contains('seg-option')) control.setAttribute('aria-pressed', String(active));
        });
        document.querySelectorAll('[data-public-visible-when], [data-public-hidden-when]').forEach(function (element) {
            var visibleRule = element.dataset.publicVisibleWhen;
            var hiddenRule = element.dataset.publicHiddenWhen;
            if (visibleRule) {
                var visibleParts = visibleRule.split('=');
                element.style.display = simpleValue(confirmed[visibleParts[0]]) === visibleParts[1] ? '' : 'none';
            } else if (hiddenRule) {
                var hiddenParts = hiddenRule.split('=');
                element.style.display = simpleValue(confirmed[hiddenParts[0]]) === hiddenParts[1] ? 'none' : '';
            }
        });
    }

    function showFeedback(state, text) {
        feedback.dataset.state = state;
        feedback.setAttribute('role', state === 'error' ? 'alert' : 'status');
        message.textContent = text;
        retryButton.hidden = state !== 'error' || !failedRequest;
        retryButton.disabled = false;
        feedback.hidden = false;
    }

    function hideFeedback() {
        feedback.hidden = true;
        delete feedback.dataset.state;
    }

    function snapshotFor(detail) {
        var config = detail.requestConfig || {};
        var source = detail.elt || config.elt || null;
        var values = copyParameters(config.parameters);
        if (source && source.name && (source.type === 'checkbox' || source.type === 'radio')) {
            values[source.name] = controlValue(source);
        }
        if (source && source.dataset.publicStateKey) {
            values[source.dataset.publicStateKey] = source.dataset.publicStateValue || controlValue(source);
        }
        var target = detail.target;
        return {
            source: source,
            target: target,
            targetSelector: target && target.id ? '#' + CSS.escape(target.id) : null,
            path: config.path || (source && source.getAttribute('hx-get')) || window.location.pathname,
            swap: config.swapSpecification && config.swapSpecification.swapStyle || 'innerHTML',
            values: values,
            history: source && source.dataset.publicHistory || (
                source && source.matches('input[type="text"], input[type="number"], input[type="range"]') ? 'replace' : 'push'
            ),
        };
    }

    function canonicalUrl() {
        var url = new URL(window.location.href);
        keys.forEach(function (key) { url.searchParams.delete(key); });
        keys.forEach(function (key) {
            var value = confirmed[key];
            if (value !== undefined && value !== null && value !== '') url.searchParams.set(key, value);
        });
        return url;
    }

    function isLatest(snapshot) {
        return !snapshot.target || latestByTarget.get(snapshot.target) === snapshot;
    }

    function commit(snapshot) {
        keys.forEach(function (key) {
            if (Object.prototype.hasOwnProperty.call(snapshot.values, key)) confirmed[key] = snapshot.values[key];
        });
        Object.keys(snapshot.responseValues || {}).forEach(function (key) {
            confirmed[key] = snapshot.responseValues[key];
        });
        applyConfirmedControls(snapshot);
        rememberControls();
        syncSelections();
        var url = canonicalUrl();
        history[snapshot.history === 'replace' ? 'replaceState' : 'pushState']({}, '', url);
        failedRequest = null;
        document.dispatchEvent(new CustomEvent('public-state:commit', {
            detail: { state: Object.assign({}, confirmed), url: url.toString() },
        }));
    }

    function fail(snapshot) {
        if (!snapshot || !isLatest(snapshot)) return;
        snapshot.failed = true;
        failedRequest = snapshot;
        restoreControls();
        showFeedback('error', "Couldn't load that view. The previous view is still shown.");
        retryButton.focus({ preventScroll: true });
    }

    document.addEventListener('htmx:beforeRequest', function (event) {
        var detail = event.detail;
        var config = detail.requestConfig || {};
        if (simpleValue(config.verb).toLowerCase() !== 'get') return;
        var retrying = Boolean(retryPending);
        var snapshot = retryPending || snapshotFor(detail);
        retryPending = null;
        snapshot.committed = false;
        snapshot.failed = false;
        snapshot.completed = false;
        snapshot.retrying = retrying;
        snapshot.responseValues = {};
        config._publicSnapshot = snapshot;
        requests.set(detail.xhr, snapshot);
        var target = snapshot.target;
        if (target) {
            latestByTarget.set(target, snapshot);
            targetCounts.set(target, (targetCounts.get(target) || 0) + 1);
            target.setAttribute('aria-busy', 'true');
        }
        pendingCount += 1;
        // Routine reads keep the current view stable while the replacement is
        // fetched. aria-busy exposes progress without inserting a banner that
        // shifts the page; this region is reserved for actionable failures.
        // A Retry keeps its existing error in place, but cannot be double-fired.
        if (retrying) retryButton.disabled = true;
        else hideFeedback();
    });

    document.addEventListener('htmx:beforeSwap', function (event) {
        var detail = event.detail;
        var snapshot = detail.requestConfig && detail.requestConfig._publicSnapshot;
        if (!snapshot) snapshot = requests.get(detail.xhr);
        if (!snapshot) return;
        if (!isLatest(snapshot)) {
            detail.shouldSwap = false;
            return;
        }
        collectResponseState(snapshot, detail.xhr && detail.xhr.responseText);
        if (detail.xhr && detail.xhr.responseText.includes('data-public-response-error')) {
            detail.shouldSwap = false;
            fail(snapshot);
        }
    });

    document.addEventListener('htmx:afterSwap', function (event) {
        var snapshot = event.detail.requestConfig && event.detail.requestConfig._publicSnapshot;
        if (!snapshot) snapshot = requests.get(event.detail.xhr);
        if (snapshot && isLatest(snapshot)) {
            var responseTarget = event.detail.target;
            if (responseTarget && responseTarget.id) {
                responseTarget = document.getElementById(responseTarget.id) || responseTarget;
            }
            if (responseTarget) {
                collectControlState(responseTarget, snapshot.responseValues);
                collectAnnotatedState(responseTarget, snapshot.responseValues, false);
            }
        }
        // One response may perform several OOB swaps before its main target.
        // Only the declared HTMX target represents the committed view; pushing
        // for every OOB title/header swap creates duplicate Back-stack entries.
        if (snapshot && isLatest(snapshot) && !snapshot.committed && event.detail.target === snapshot.target) {
            snapshot.committed = true;
            commit(snapshot);
        }
    });

    document.addEventListener('htmx:afterRequest', function (event) {
        var snapshot = event.detail.requestConfig && event.detail.requestConfig._publicSnapshot;
        if (!snapshot) snapshot = requests.get(event.detail.xhr);
        if (!snapshot) return;
        if (!snapshot.completed) {
            snapshot.completed = true;
            pendingCount = Math.max(0, pendingCount - 1);
        }
        var target = snapshot.target;
        if (target) {
            var remaining = Math.max(0, (targetCounts.get(target) || 1) - 1);
            targetCounts.set(target, remaining);
            target.setAttribute('aria-busy', String(remaining > 0));
        }
        if (event.detail.failed && isLatest(snapshot)) fail(snapshot);
        if (pendingCount === 0 && !failedRequest) hideFeedback();
        requests.delete(event.detail.xhr);
    });

    function transportFailure(event) {
        var snapshot = event.detail && event.detail.requestConfig && event.detail.requestConfig._publicSnapshot;
        if (!snapshot && event.detail && event.detail.xhr) snapshot = requests.get(event.detail.xhr);
        if (!snapshot && event.detail) snapshot = snapshotFor(event.detail);
        if (snapshot && isLatest(snapshot)) fail(snapshot);
    }
    document.addEventListener('htmx:responseError', transportFailure);
    document.addEventListener('htmx:sendError', transportFailure);
    document.addEventListener('htmx:sendAbort', transportFailure);
    document.addEventListener('htmx:timeout', transportFailure);

    retryButton.addEventListener('click', function () {
        if (!failedRequest || !failedRequest.targetSelector) return;
        retryPending = failedRequest;
        htmx.ajax('GET', failedRequest.path, {
            source: failedRequest.source || root,
            target: failedRequest.targetSelector,
            swap: failedRequest.swap,
            values: failedRequest.values,
        });
    });
    dismissButton.addEventListener('click', hideFeedback);
    window.addEventListener('popstate', function () { window.location.reload(); });

    // The server-rendered DOM is authoritative. Do not seed from raw query
    // values: the route may have normalised an invalid or unavailable value.
    collectControlState(document, confirmed);
    collectAnnotatedState(document, confirmed, true);
    rememberControls();
    syncSelections();
    history.replaceState({}, '', canonicalUrl());
})();

/* /records stacked lists (mobile): show each holder's occasions beside the
   name while every row fits on one line; as soon as any row on the page
   would overflow, wrap them all under their names (.is-wrapped) so rows
   never mix the two forms. Re-checked after HTMX tab swaps and resizes. */
(function () {
    function fitStackedRecords() {
        document.querySelectorAll('.records-page').forEach(function (page) {
            var lists = page.querySelectorAll('.records-list--stacked');
            if (!lists.length) return;
            lists.forEach(function (list) { list.classList.remove('is-wrapped'); });
            var overflows = Array.from(page.querySelectorAll('.records-list--stacked .rec-holder'))
                .some(function (row) { return row.scrollWidth > row.clientWidth + 1; });
            lists.forEach(function (list) { list.classList.toggle('is-wrapped', overflows); });
        });
    }
    var timer = null;
    window.addEventListener('resize', function () {
        clearTimeout(timer);
        timer = setTimeout(fitStackedRecords, 100);
    });
    document.addEventListener('htmx:afterSwap', fitStackedRecords);
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', fitStackedRecords);
    } else {
        fitStackedRecords();
    }
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(fitStackedRecords);
})();
