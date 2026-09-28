from backend.database.cache import Cache


def test_memory_cache_roundtrip():
    cache = Cache(force_memory=True, ttl=30)
    assert cache.backend == "memory"
    cache.set("rank:sol", {"n": 1})
    assert cache.get("rank:sol") == {"n": 1}
    cache.delete("rank:sol")
    assert cache.get("rank:sol") is None


def test_memory_cache_expires(monkeypatch):
    now = {"t": 100.0}
    monkeypatch.setattr("backend.database.cache.time.monotonic", lambda: now["t"])
    cache = Cache(force_memory=True, ttl=5)
    cache.set("k", [1, 2])
    now["t"] = 106.0
    assert cache.get("k") is None
