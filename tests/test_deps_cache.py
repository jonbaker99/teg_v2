"""The cross-module cache-clear registry in webapp.deps.

Route modules keep their own lru_cache'd accessors (deps can't import routes
without a circular import), so they register their cache_clear with deps and
clear_all_data_caches() must fan out to them. This guards the specific bug
that motivated the registry: player.py's winners cache going stale after a
data update.
"""

import importlib


def test_clear_all_data_caches_invalidates_registered_route_caches():
    from webapp import deps
    player = importlib.import_module("webapp.routes.player")

    # player.py registers its winners cache at import time.
    assert player._get_winners_data.cache_clear in deps._extra_cache_clearers

    player._get_winners_data()
    assert player._get_winners_data.cache_info().currsize == 1

    deps.clear_all_data_caches()
    assert player._get_winners_data.cache_info().currsize == 0


def test_register_cache_clearer_is_idempotent():
    from webapp import deps

    calls = []
    clearer = lambda: calls.append(1)  # noqa: E731

    deps.register_cache_clearer(clearer)
    deps.register_cache_clearer(clearer)  # second registration is a no-op
    assert deps._extra_cache_clearers.count(clearer) == 1

    deps.clear_all_data_caches()
    assert calls == [1]  # invoked exactly once

    deps._extra_cache_clearers.remove(clearer)  # keep global state clean
