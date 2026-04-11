"""tests/test_model_router.py — Tests for the AURA ModelRouter (v0.4.0)."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from aura.model.router import ModelRouter, build_router_from_config, build_default_free_router
from aura.model.dummy import EchoModelBackend


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_backend(available: bool = True, reply: str = "hello") -> MagicMock:
    b = MagicMock()
    b.is_available.return_value = available
    b.complete.return_value = reply
    return b


def _make_failing_backend(exc: Exception = RuntimeError("fail")) -> MagicMock:
    b = MagicMock()
    b.is_available.return_value = True
    b.complete.side_effect = exc
    return b


# ── ModelRouter tests ──────────────────────────────────────────────────────────

class TestModelRouter:

    def test_returns_first_successful_reply(self):
        b1 = _make_backend(reply="from b1")
        b2 = _make_backend(reply="from b2")
        router = ModelRouter([("b1", b1), ("b2", b2)])
        result = router.complete([{"role": "user", "content": "hi"}])
        assert result == "from b1"
        b1.complete.assert_called_once()
        b2.complete.assert_not_called()

    def test_skips_failing_backends(self):
        b1 = _make_failing_backend()
        b2 = _make_backend(reply="from b2")
        router = ModelRouter([("b1", b1), ("b2", b2)])
        result = router.complete([{"role": "user", "content": "hi"}])
        assert result == "from b2"

    def test_raises_when_all_fail(self):
        b1 = _make_failing_backend(RuntimeError("oops1"))
        b2 = _make_failing_backend(RuntimeError("oops2"))
        router = ModelRouter([("b1", b1), ("b2", b2)])
        with pytest.raises(RuntimeError, match="All model backends failed"):
            router.complete([{"role": "user", "content": "hi"}])

    def test_is_available_true_if_any_available(self):
        b1 = _make_backend(available=False)
        b2 = _make_backend(available=True)
        router = ModelRouter([("b1", b1), ("b2", b2)])
        assert router.is_available() is True

    def test_is_available_false_if_none_available(self):
        b1 = _make_backend(available=False)
        b2 = _make_backend(available=False)
        router = ModelRouter([("b1", b1), ("b2", b2)])
        assert router.is_available() is False

    def test_backend_status_returns_list(self):
        b1 = _make_backend(available=True)
        b2 = _make_backend(available=False)
        router = ModelRouter([("primary", b1), ("fallback", b2)])
        status = router.backend_status()
        assert len(status) == 2
        assert status[0]["name"] == "primary"
        assert status[0]["available"] is True
        assert status[1]["name"] == "fallback"
        assert status[1]["available"] is False

    def test_list_backends(self):
        b1 = _make_backend()
        b2 = _make_backend()
        router = ModelRouter([("alpha", b1), ("beta", b2)])
        assert router.list_backends() == ["alpha", "beta"]

    def test_repr_contains_names(self):
        router = ModelRouter([("x", _make_backend()), ("y", _make_backend())])
        assert "x" in repr(router)
        assert "y" in repr(router)

    def test_single_backend(self):
        b = _make_backend(reply="solo")
        router = ModelRouter([("only", b)])
        assert router.complete([]) == "solo"

    def test_empty_backends_raises(self):
        router = ModelRouter([])
        with pytest.raises(RuntimeError):
            router.complete([])


# ── build_router_from_config tests ────────────────────────────────────────────

class TestBuildRouterFromConfig:

    def test_builds_echo_when_no_url(self):
        cfg = [{"name": "echo", "base_url": ""}]
        router = build_router_from_config(cfg)
        assert isinstance(router, ModelRouter)
        # Echo backend should be reachable
        assert router.is_available() is True

    def test_builds_echo_fallback_when_empty_cfg(self):
        router = build_router_from_config([])
        assert isinstance(router, ModelRouter)
        assert router.is_available() is True

    def test_builds_remote_backends(self):
        cfg = [
            {
                "name": "test_remote",
                "base_url": "http://localhost:9999/v1",
                "api_key": "test-key",
                "model_name": "test-model",
            },
            {"name": "echo", "base_url": ""},
        ]
        router = build_router_from_config(cfg)
        backends = router.list_backends()
        assert "test_remote" in backends
        assert "echo" in backends

    def test_resolves_api_key_from_env(self, monkeypatch):
        monkeypatch.setenv("TEST_KEY_ENV", "my-secret-key")
        cfg = [
            {
                "name": "remote",
                "base_url": "http://example.com/v1",
                "api_key_env": "TEST_KEY_ENV",
                "model_name": "test",
            },
        ]
        router = build_router_from_config(cfg)
        # We can't easily inspect the key, but construction should succeed
        assert isinstance(router, ModelRouter)

    def test_default_free_router_builds(self):
        router = build_default_free_router()
        assert isinstance(router, ModelRouter)
        # Should always have at least the echo backend
        assert router.is_available() is True
        # Should have all expected backends
        backends = router.list_backends()
        assert "echo" in backends
        assert "groq" in backends
        assert "openrouter" in backends
