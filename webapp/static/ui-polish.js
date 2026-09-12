/* Native disclosure navigation and read-only HTMX request feedback. */
(function () {
    var hamburger = document.querySelector('.nav-hamburger');
    var links = document.querySelector('.nav-links');
    var menus = Array.from(document.querySelectorAll('.nav-dropdown'));
    function closeMenus() {
        menus.forEach(function (menu) {
            menu.classList.remove('open');
            menu.querySelector('button').setAttribute('aria-expanded', 'false');
        });
    }
    hamburger.addEventListener('click', function () {
        var open = links.classList.toggle('open');
        hamburger.setAttribute('aria-expanded', String(open));
        hamburger.setAttribute('aria-label', open ? 'Close navigation' : 'Open navigation');
        if (!open) closeMenus();
    });
    menus.forEach(function (menu) {
        var button = menu.querySelector('button');
        button.addEventListener('click', function () {
            var open = !menu.classList.contains('open');
            closeMenus();
            menu.classList.toggle('open', open);
            button.setAttribute('aria-expanded', String(open));
        });
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
    /* Track read requests only: never automatically retry a data write. */
    var requests = new WeakMap();
    var counts = new WeakMap();
    var failedTarget = null;
    var feedback = document.getElementById('request-feedback');
    feedback.querySelector('button').addEventListener('click', function () { feedback.hidden = true; });
    document.addEventListener('htmx:beforeRequest', function (event) {
        var detail = event.detail;
        if (detail.requestConfig.verb.toLowerCase() !== 'get') return;
        var target = detail.target;
        requests.set(detail.xhr, target);
        counts.set(target, (counts.get(target) || 0) + 1);
        target.setAttribute('aria-busy', 'true');
    });
    document.addEventListener('htmx:afterRequest', function (event) {
        var detail = event.detail;
        var target = requests.get(detail.xhr);
        if (!target) return;
        requests.delete(detail.xhr);
        var remaining = Math.max(0, (counts.get(target) || 1) - 1);
        counts.set(target, remaining);
        target.setAttribute('aria-busy', String(remaining > 0));
        if (detail.successful && target === failedTarget) {
            feedback.hidden = true;
            failedTarget = null;
        }
        if (detail.failed) {
            failedTarget = target;
            feedback.querySelector('span').textContent = 'This view could not be loaded. Check your connection and choose the view again.';
            feedback.hidden = false;
        }
    });
})();
