from app.services.rate_limit import SlidingWindow
from app.settings import DEFAULT_CORS_ORIGINS, Settings


def test_defaults_are_safe_for_local_dev(monkeypatch):
    for name in ("ENVIRONMENT", "CORS_ORIGINS"):
        monkeypatch.delenv(name, raising=False)
    s = Settings()
    assert not s.is_production
    assert "*" not in s.cors_origins and s.cors_origins == DEFAULT_CORS_ORIGINS.split(",")


def test_production_flag(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "Production")
    assert Settings().is_production


def test_sliding_window_forgets_old_hits(monkeypatch):
    now = [1000.0]
    monkeypatch.setattr("app.services.rate_limit.time.monotonic", lambda: now[0])
    w = SlidingWindow(window_seconds=60)
    w.hit("a")
    w.hit("a")
    assert w.count("a") == 2 and w.count("b") == 0
    now[0] += 61
    assert w.count("a") == 0
