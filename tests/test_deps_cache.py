"""The cross-module cache-clear registry in webapp.deps.

Route modules can keep their own lru_cache'd accessors (deps can't import
routes without a circular import), so they'd register their cache_clear with
deps and clear_all_data_caches() must fan out to them. Also guards that
deps' own lru_cache'd accessors -- including cached_winners() and
cached_streaks_data(), shared by /honours, /player and the /latest-* tabs --
are invalidated after a data update.
"""

import importlib


def test_clear_all_data_caches_invalidates_own_caches():
    from webapp import deps
    importlib.import_module("webapp.routes.player")

    deps.cached_winners()
    assert deps.cached_winners.cache_info().currsize == 1

    deps.clear_all_data_caches()
    assert deps.cached_winners.cache_info().currsize == 0


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
