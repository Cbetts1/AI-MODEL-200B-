"""tests/test_virtual_cloud.py — Tests for AURA v0.7.0 virtual cloud infrastructure.

Covers:
  • VirtualCPU    — task scheduling, expand/shrink, stats
  • VirtualNetwork — address registration, send/recv, broadcast, port allocation
  • VirtualServer  — route registration, handle, lifecycle
  • CloudRouter    — add/remove/match routes, prefix fallback, stats
  • VirtualStorage — CRUD, namespaces, snapshot/restore, stats
  • CloudManager   — start/stop, spawn/destroy servers, build actions, status
  • API endpoints  — /v1/cloud/* via AuraAPIHandler
"""

from __future__ import annotations

import io
import json
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ── VirtualCPU ─────────────────────────────────────────────────────────────────

from aura.cloud.virtual_cpu import VirtualCPU


class TestVirtualCPU:
    def test_submit_returns_future(self):
        cpu = VirtualCPU(workers=2)
        future = cpu.submit(lambda: 42)
        assert future.result(timeout=2) == 42
        cpu.shutdown()

    def test_stats_reflect_activity(self):
        cpu = VirtualCPU(workers=2, name="test-cpu")
        event = threading.Event()
        cpu.submit(lambda: event.wait(2))
        time.sleep(0.05)
        stats = cpu.stats()
        assert stats["name"] == "test-cpu"
        assert stats["workers"] == 2
        assert stats["active"] is True
        event.set()
        cpu.shutdown()

    def test_completed_counter_increments(self):
        cpu = VirtualCPU(workers=2)
        futures = [cpu.submit(lambda: None) for _ in range(5)]
        for f in futures:
            f.result(timeout=2)
        stats = cpu.stats()
        assert stats["completed"] == 5
        cpu.shutdown()

    def test_failed_counter_increments(self):
        cpu = VirtualCPU(workers=2)
        future = cpu.submit(lambda: 1 / 0)
        with pytest.raises(ZeroDivisionError):
            future.result(timeout=2)
        stats = cpu.stats()
        assert stats["failed"] == 1
        cpu.shutdown()

    def test_expand_increases_workers(self):
        cpu = VirtualCPU(workers=2)
        new_count = cpu.expand(2)
        assert new_count == 4
        cpu.shutdown()

    def test_shrink_decreases_workers(self):
        cpu = VirtualCPU(workers=4)
        new_count = cpu.shrink(2)
        assert new_count == 2
        cpu.shutdown()

    def test_shrink_never_below_one(self):
        cpu = VirtualCPU(workers=1)
        new_count = cpu.shrink(100)
        assert new_count == 1
        cpu.shutdown()

    def test_shutdown_prevents_new_tasks(self):
        cpu = VirtualCPU(workers=2)
        cpu.shutdown()
        with pytest.raises(RuntimeError):
            cpu.submit(lambda: None)

    def test_invalid_workers_raises(self):
        with pytest.raises(ValueError):
            VirtualCPU(workers=0)

    def test_expand_invalid_raises(self):
        cpu = VirtualCPU(workers=2)
        with pytest.raises(ValueError):
            cpu.expand(0)
        cpu.shutdown()

    def test_uptime_positive(self):
        cpu = VirtualCPU(workers=1)
        time.sleep(0.01)
        assert cpu.stats()["uptime_seconds"] > 0
        cpu.shutdown()


# ── VirtualNetwork ─────────────────────────────────────────────────────────────

from aura.cloud.virtual_network import VirtualNetwork


class TestVirtualNetwork:
    def test_register_returns_address(self):
        net = VirtualNetwork()
        addr = net.register_address("srv-a")
        assert "srv-a" in addr
        assert addr.startswith("vnet://")

    def test_register_idempotent(self):
        net = VirtualNetwork()
        addr1 = net.register_address("srv-a")
        addr2 = net.register_address("srv-a")
        assert addr1 == addr2

    def test_send_and_recv(self):
        net = VirtualNetwork()
        net.register_address("a")
        net.register_address("b")
        assert net.send("a", "b", {"hello": "world"})
        msg = net.recv("b", timeout=0.5)
        assert msg is not None
        assert msg["payload"] == {"hello": "world"}
        assert msg["src"] == "a"
        assert msg["dst"] == "b"

    def test_recv_no_message_returns_none(self):
        net = VirtualNetwork()
        net.register_address("empty")
        assert net.recv("empty", timeout=0.05) is None

    def test_send_to_unknown_returns_false(self):
        net = VirtualNetwork()
        net.register_address("a")
        assert not net.send("a", "nonexistent", {})

    def test_broadcast(self):
        net = VirtualNetwork()
        net.register_address("src")
        net.register_address("dst1")
        net.register_address("dst2")
        count = net.broadcast("src", {"ping": True})
        assert count == 2
        for dst in ("dst1", "dst2"):
            msg = net.recv(dst, timeout=0.5)
            assert msg is not None

    def test_broadcast_excludes_sender(self):
        net = VirtualNetwork()
        net.register_address("only")
        count = net.broadcast("only", {"ping": True})
        assert count == 0

    def test_unregister(self):
        net = VirtualNetwork()
        net.register_address("gone")
        assert net.unregister_address("gone")
        assert not net.unregister_address("gone")

    def test_allocate_port(self):
        net = VirtualNetwork()
        p1 = net.allocate_port()
        p2 = net.allocate_port()
        assert p1 != p2
        assert 40000 <= p1 <= 49999
        assert 40000 <= p2 <= 49999

    def test_release_port(self):
        net = VirtualNetwork()
        p = net.allocate_port()
        assert net.release_port(p)
        assert not net.release_port(p)  # already released

    def test_status(self):
        net = VirtualNetwork(name="test-net")
        net.register_address("alpha")
        s = net.status()
        assert s["name"] == "test-net"
        assert "alpha" in s["servers"]
        assert s["total_messages_routed"] == 0

    def test_total_messages_increments(self):
        net = VirtualNetwork()
        net.register_address("x")
        net.register_address("y")
        net.send("x", "y", "msg1")
        net.send("x", "y", "msg2")
        assert net.status()["total_messages_routed"] == 2

    def test_list_servers(self):
        net = VirtualNetwork()
        net.register_address("s1")
        net.register_address("s2")
        assert set(net.list_servers()) == {"s1", "s2"}


# ── CloudRouter ────────────────────────────────────────────────────────────────

from aura.cloud.router import CloudRouter


class TestCloudRouter:
    def test_add_and_match_exact(self):
        r = CloudRouter()
        r.add_route("GET /ping", lambda req: "pong")
        handler = r.match("GET /ping")
        assert handler is not None
        assert handler({}) == "pong"

    def test_match_returns_none_for_missing(self):
        r = CloudRouter()
        assert r.match("GET /missing") is None

    def test_remove_route(self):
        r = CloudRouter()
        r.add_route("GET /bye", lambda req: "bye")
        assert r.remove_route("GET /bye")
        assert r.match("GET /bye") is None

    def test_remove_nonexistent(self):
        r = CloudRouter()
        assert not r.remove_route("GET /ghost")

    def test_prefix_match(self):
        r = CloudRouter()
        r.add_route("GET /api", lambda req: "api-root")
        handler = r.match("GET /api/v1/things")
        assert handler is not None
        assert handler({}) == "api-root"

    def test_exact_wins_over_prefix(self):
        r = CloudRouter()
        r.add_route("GET /api", lambda req: "prefix")
        r.add_route("GET /api/exact", lambda req: "exact")
        handler = r.match("GET /api/exact")
        assert handler({}) == "exact"

    def test_replace_default_true(self):
        r = CloudRouter()
        r.add_route("GET /x", lambda req: "old")
        r.add_route("GET /x", lambda req: "new")
        assert r.match("GET /x")({}) == "new"

    def test_no_replace(self):
        r = CloudRouter()
        r.add_route("GET /x", lambda req: "original")
        added = r.add_route("GET /x", lambda req: "new", replace=False)
        assert not added
        assert r.match("GET /x")({}) == "original"

    def test_list_routes(self):
        r = CloudRouter()
        r.add_route("GET /a", lambda req: None, description="route a")
        r.add_route("POST /b", lambda req: None, description="route b")
        routes = r.list_routes()
        assert len(routes) == 2
        route_keys = [ro["route"] for ro in routes]
        assert "GET /a" in route_keys
        assert "POST /b" in route_keys

    def test_route_count(self):
        r = CloudRouter()
        assert r.route_count() == 0
        r.add_route("GET /z", lambda req: None)
        assert r.route_count() == 1

    def test_stats(self):
        r = CloudRouter()
        r.add_route("GET /s", lambda req: None)
        r.match("GET /s")
        stats = r.stats()
        assert stats["route_count"] == 1
        assert stats["total_lookups"] >= 1


# ── VirtualServer ──────────────────────────────────────────────────────────────

from aura.cloud.virtual_server import VirtualServer


class TestVirtualServer:
    def _make_server(self, name="test-srv"):
        net = VirtualNetwork()
        srv = VirtualServer(name=name, network=net)
        return srv, net

    def test_handle_registered_route(self):
        srv, _ = self._make_server()
        srv.register_route("GET /ping", lambda req: {"pong": True})
        resp = srv.handle({"method": "GET", "path": "/ping"})
        assert resp["status"] == 200
        assert resp["body"] == {"pong": True}

    def test_handle_unknown_route_404(self):
        srv, _ = self._make_server()
        resp = srv.handle({"method": "GET", "path": "/missing"})
        assert resp["status"] == 404

    def test_handle_handler_exception_500(self):
        srv, _ = self._make_server()
        srv.register_route("GET /boom", lambda req: 1 / 0)
        resp = srv.handle({"method": "GET", "path": "/boom"})
        assert resp["status"] == 500

    def test_unregister_route(self):
        srv, _ = self._make_server()
        srv.register_route("GET /bye", lambda req: {})
        assert srv.unregister_route("GET /bye")
        resp = srv.handle({"method": "GET", "path": "/bye"})
        assert resp["status"] == 404

    def test_start_stop(self):
        srv, _ = self._make_server()
        srv.start()
        assert srv._running
        srv.stop()
        assert not srv._running

    def test_status(self):
        srv, _ = self._make_server("my-server")
        srv.register_route("GET /x", lambda req: {})
        s = srv.status()
        assert s["name"] == "my-server"
        assert s["running"] is False
        assert len(s["routes"]) == 1

    def test_network_messaging(self):
        net = VirtualNetwork()
        srv = VirtualServer("echo-srv", net, auto_start=True)
        srv.register_route("GET /echo", lambda req: {"echoed": req.get("body")})
        net.register_address("client")
        net.send("client", "echo-srv", {"method": "GET", "path": "/echo", "body": "hello"})
        # Give the background thread time to process
        time.sleep(0.2)
        response = net.recv("client", timeout=0.5)
        assert response is not None
        assert response["payload"]["status"] == 200
        srv.stop()

    def test_requests_handled_counter(self):
        srv, _ = self._make_server()
        srv.register_route("GET /a", lambda req: {})
        srv.handle({"method": "GET", "path": "/a"})
        srv.handle({"method": "GET", "path": "/missing"})
        s = srv.status()
        assert s["requests_handled"] == 2


# ── VirtualStorage ─────────────────────────────────────────────────────────────

from aura.cloud.virtual_storage import VirtualStorage


class TestVirtualStorage:
    def _make_storage(self, tmp_path: Path):
        return VirtualStorage(db_path=tmp_path / "test.db")

    def test_put_and_get(self, tmp_path):
        vs = self._make_storage(tmp_path)
        vs.put("ns1", "key1", {"val": 42})
        assert vs.get("ns1", "key1") == {"val": 42}
        vs.close()

    def test_get_missing_returns_none(self, tmp_path):
        vs = self._make_storage(tmp_path)
        assert vs.get("ns1", "missing") is None
        vs.close()

    def test_delete(self, tmp_path):
        vs = self._make_storage(tmp_path)
        vs.put("ns", "k", "v")
        assert vs.delete("ns", "k")
        assert not vs.delete("ns", "k")
        vs.close()

    def test_keys(self, tmp_path):
        vs = self._make_storage(tmp_path)
        vs.put("ns", "b", 2)
        vs.put("ns", "a", 1)
        assert vs.keys("ns") == ["a", "b"]
        vs.close()

    def test_all_items(self, tmp_path):
        vs = self._make_storage(tmp_path)
        vs.put("ns", "x", 10)
        vs.put("ns", "y", 20)
        items = vs.all_items("ns")
        assert items == {"x": 10, "y": 20}
        vs.close()

    def test_namespaces(self, tmp_path):
        vs = self._make_storage(tmp_path)
        vs.put("alpha", "k", 1)
        vs.put("beta", "k", 2)
        ns = vs.namespaces()
        assert "alpha" in ns
        assert "beta" in ns
        vs.close()

    def test_clear_namespace(self, tmp_path):
        vs = self._make_storage(tmp_path)
        vs.put("todel", "a", 1)
        vs.put("todel", "b", 2)
        removed = vs.clear_namespace("todel")
        assert removed == 2
        assert vs.keys("todel") == []
        vs.close()

    def test_snapshot_and_restore(self, tmp_path):
        vs = self._make_storage(tmp_path)
        vs.put("snap", "x", 1)
        vs.put("snap", "y", 2)
        snap = vs.snapshot()
        assert snap == {"snap": {"x": 1, "y": 2}}
        # Restore into a fresh store
        vs2 = VirtualStorage(db_path=tmp_path / "restore.db")
        count = vs2.restore(snap)
        assert count == 2
        assert vs2.get("snap", "x") == 1
        vs.close()
        vs2.close()

    def test_usage(self, tmp_path):
        vs = self._make_storage(tmp_path)
        vs.put("u", "k", "hello")
        usage = vs.usage()
        assert "u" in usage
        assert usage["u"]["keys"] == 1
        assert usage["u"]["size_bytes"] > 0
        vs.close()

    def test_stats(self, tmp_path):
        vs = self._make_storage(tmp_path)
        vs.put("s", "k", "v")
        vs.get("s", "k")
        stats = vs.stats()
        assert stats["total_writes"] >= 1
        assert stats["total_reads"] >= 1
        vs.close()


# ── CloudManager ───────────────────────────────────────────────────────────────

from aura.cloud.cloud_manager import CloudManager


class TestCloudManager:
    def _make_manager(self, tmp_path: Path):
        return CloudManager(cpu_workers=2, storage_db_path=tmp_path / "cloud.db")

    def test_start_stop(self, tmp_path):
        cm = self._make_manager(tmp_path)
        cm.start()
        assert cm._running
        cm.stop()
        assert not cm._running

    def test_spawn_server(self, tmp_path):
        cm = self._make_manager(tmp_path)
        cm.start()
        srv = cm.spawn_server("worker-1")
        assert srv.name == "worker-1"
        assert "worker-1" in [s["name"] for s in cm.list_servers()]
        cm.stop()

    def test_spawn_server_idempotent(self, tmp_path):
        cm = self._make_manager(tmp_path)
        cm.start()
        srv1 = cm.spawn_server("w")
        srv2 = cm.spawn_server("w")
        assert srv1 is srv2
        cm.stop()

    def test_destroy_server(self, tmp_path):
        cm = self._make_manager(tmp_path)
        cm.start()
        cm.spawn_server("to-kill")
        assert cm.destroy_server("to-kill")
        assert "to-kill" not in [s["name"] for s in cm.list_servers()]
        cm.stop()

    def test_destroy_nonexistent_returns_false(self, tmp_path):
        cm = self._make_manager(tmp_path)
        cm.start()
        assert not cm.destroy_server("ghost")
        cm.stop()

    def test_submit_task(self, tmp_path):
        cm = self._make_manager(tmp_path)
        cm.start()
        future = cm.submit_task(lambda: "done")
        assert future.result(timeout=2) == "done"
        cm.stop()

    def test_add_and_remove_route(self, tmp_path):
        cm = self._make_manager(tmp_path)
        cm.start()
        assert cm.add_route("GET /test", lambda req: "test", description="test route")
        assert cm.router.match("GET /test") is not None
        assert cm.remove_route("GET /test")
        assert cm.router.match("GET /test") is None
        cm.stop()

    def test_build_expand_cpu(self, tmp_path):
        cm = self._make_manager(tmp_path)
        cm.start()
        result = cm.build("expand_cpu", n=2)
        assert result["new_worker_count"] == 4
        cm.stop()

    def test_build_shrink_cpu(self, tmp_path):
        cm = self._make_manager(tmp_path)
        cm.start()
        result = cm.build("shrink_cpu", n=1)
        assert result["new_worker_count"] == 1
        cm.stop()

    def test_build_add_storage_namespace(self, tmp_path):
        cm = self._make_manager(tmp_path)
        cm.start()
        result = cm.build("add_storage_namespace", name="my-ns")
        assert result["created"] is True
        cm.stop()

    def test_build_add_server(self, tmp_path):
        cm = self._make_manager(tmp_path)
        cm.start()
        result = cm.build("add_server", name="new-srv")
        assert result["server"]["name"] == "new-srv"
        cm.stop()

    def test_build_remove_server(self, tmp_path):
        cm = self._make_manager(tmp_path)
        cm.start()
        cm.spawn_server("doomed")
        result = cm.build("remove_server", name="doomed")
        assert result["removed"] is True
        cm.stop()

    def test_build_unknown_action(self, tmp_path):
        cm = self._make_manager(tmp_path)
        cm.start()
        result = cm.build("fly_to_the_moon")
        assert "error" in result
        cm.stop()

    def test_status_shape(self, tmp_path):
        cm = self._make_manager(tmp_path)
        cm.start()
        s = cm.status()
        assert s["running"] is True
        assert "cpu" in s
        assert "network" in s
        assert "router" in s
        assert "storage" in s
        assert "servers" in s
        cm.stop()

    def test_builtin_routes_registered(self, tmp_path):
        cm = self._make_manager(tmp_path)
        assert cm.router.match("GET /cloud/ping") is not None
        assert cm.router.match("GET /cloud/status") is not None
        cm.stop()

    def test_storage_persists_server_record(self, tmp_path):
        cm = self._make_manager(tmp_path)
        cm.start()
        cm.spawn_server("stored-srv")
        record = cm.storage.get("cloud:servers", "stored-srv")
        assert record is not None
        assert record["name"] == "stored-srv"
        cm.stop()


# ── API endpoints ──────────────────────────────────────────────────────────────

from http import HTTPStatus


def _make_engine_with_cloud(tmp_path: Path):
    """Return a minimal mock engine with a real CloudManager."""
    from unittest.mock import MagicMock
    from aura.cloud.cloud_manager import CloudManager

    engine = MagicMock()
    engine.cloud = CloudManager(cpu_workers=2, storage_db_path=tmp_path / "api_cloud.db")
    engine.cloud.start()
    return engine


def _make_handler(engine, method="GET", path="/", body=None):
    """Build a minimal mock handler for testing do_GET / do_POST / do_DELETE."""
    import email
    from aura.ui.api import make_handler_class

    HandlerClass = make_handler_class(engine, api_token="", admin_token="")

    handler = HandlerClass.__new__(HandlerClass)
    handler.engine = engine
    handler.api_token = ""
    handler.admin_token = ""
    handler.path = path
    handler.request_version = "HTTP/1.1"
    handler.close_connection = True
    handler.client_address = ("127.0.0.1", 0)

    # Fake response buffer
    buf = io.BytesIO()
    handler.wfile = buf
    handler._response_status = None
    handler._response_headers = {}

    def _send_response(code, *args, **kwargs):
        handler._response_status = code

    def _send_header(k, v):
        handler._response_headers[k] = v

    def _end_headers():
        pass

    handler.send_response = _send_response
    handler.send_header = _send_header
    handler.end_headers = _end_headers

    # Fake request body
    if body is not None:
        raw = json.dumps(body).encode()
        handler.rfile = io.BytesIO(raw)
        handler.headers = email.message_from_string(f"Content-Length: {len(raw)}\r\n")
    else:
        handler.rfile = io.BytesIO(b"")
        handler.headers = email.message_from_string("")

    return handler, buf


class TestCloudAPIEndpoints:
    def test_get_cloud_status(self, tmp_path):
        engine = _make_engine_with_cloud(tmp_path)
        handler, buf = _make_handler(engine, path="/v1/cloud/status")
        handler.do_GET()
        response = json.loads(buf.getvalue())
        assert "running" in response
        assert "cpu" in response
        engine.cloud.stop()

    def test_get_cloud_cpu(self, tmp_path):
        engine = _make_engine_with_cloud(tmp_path)
        handler, buf = _make_handler(engine, path="/v1/cloud/cpu")
        handler.do_GET()
        response = json.loads(buf.getvalue())
        assert "workers" in response
        engine.cloud.stop()

    def test_get_cloud_network(self, tmp_path):
        engine = _make_engine_with_cloud(tmp_path)
        handler, buf = _make_handler(engine, path="/v1/cloud/network")
        handler.do_GET()
        response = json.loads(buf.getvalue())
        assert "servers" in response
        engine.cloud.stop()

    def test_get_cloud_storage(self, tmp_path):
        engine = _make_engine_with_cloud(tmp_path)
        handler, buf = _make_handler(engine, path="/v1/cloud/storage")
        handler.do_GET()
        response = json.loads(buf.getvalue())
        assert "stats" in response
        engine.cloud.stop()

    def test_get_cloud_servers(self, tmp_path):
        engine = _make_engine_with_cloud(tmp_path)
        handler, buf = _make_handler(engine, path="/v1/cloud/servers")
        handler.do_GET()
        response = json.loads(buf.getvalue())
        assert "servers" in response
        engine.cloud.stop()

    def test_get_cloud_routes(self, tmp_path):
        engine = _make_engine_with_cloud(tmp_path)
        handler, buf = _make_handler(engine, path="/v1/cloud/routes")
        handler.do_GET()
        response = json.loads(buf.getvalue())
        assert "routes" in response
        engine.cloud.stop()

    def test_post_cloud_servers_spawn(self, tmp_path):
        engine = _make_engine_with_cloud(tmp_path)
        handler, buf = _make_handler(engine, path="/v1/cloud/servers", body={"name": "api-srv"})
        handler.do_POST()
        response = json.loads(buf.getvalue())
        assert response["server"]["name"] == "api-srv"
        engine.cloud.stop()

    def test_post_cloud_servers_missing_name(self, tmp_path):
        engine = _make_engine_with_cloud(tmp_path)
        handler, buf = _make_handler(engine, path="/v1/cloud/servers", body={})
        handler.do_POST()
        assert handler._response_status == HTTPStatus.BAD_REQUEST
        engine.cloud.stop()

    def test_post_cloud_routes(self, tmp_path):
        engine = _make_engine_with_cloud(tmp_path)
        handler, buf = _make_handler(
            engine,
            path="/v1/cloud/routes",
            body={"route": "GET /custom", "description": "test", "response": {"ok": True}},
        )
        handler.do_POST()
        response = json.loads(buf.getvalue())
        assert response["added"] is True
        assert response["route"] == "GET /custom"
        engine.cloud.stop()

    def test_post_cloud_routes_missing_route(self, tmp_path):
        engine = _make_engine_with_cloud(tmp_path)
        handler, buf = _make_handler(engine, path="/v1/cloud/routes", body={})
        handler.do_POST()
        assert handler._response_status == HTTPStatus.BAD_REQUEST
        engine.cloud.stop()

    def test_post_cloud_build(self, tmp_path):
        engine = _make_engine_with_cloud(tmp_path)
        handler, buf = _make_handler(engine, path="/v1/cloud/build", body={"action": "expand_cpu", "n": 1})
        handler.do_POST()
        response = json.loads(buf.getvalue())
        assert "new_worker_count" in response
        engine.cloud.stop()

    def test_post_cloud_build_missing_action(self, tmp_path):
        engine = _make_engine_with_cloud(tmp_path)
        handler, buf = _make_handler(engine, path="/v1/cloud/build", body={})
        handler.do_POST()
        assert handler._response_status == HTTPStatus.BAD_REQUEST
        engine.cloud.stop()

    def test_delete_cloud_server(self, tmp_path):
        engine = _make_engine_with_cloud(tmp_path)
        engine.cloud.spawn_server("to-delete")
        handler, buf = _make_handler(engine, path="/v1/cloud/servers/to-delete")
        handler.do_DELETE()
        response = json.loads(buf.getvalue())
        assert response["removed"] is True
        engine.cloud.stop()

    def test_delete_cloud_server_missing_name(self, tmp_path):
        engine = _make_engine_with_cloud(tmp_path)
        handler, buf = _make_handler(engine, path="/v1/cloud/servers/")
        handler.do_DELETE()
        assert handler._response_status == HTTPStatus.BAD_REQUEST
        engine.cloud.stop()

    def test_delete_cloud_route(self, tmp_path):
        engine = _make_engine_with_cloud(tmp_path)
        engine.cloud.add_route("GET /del", lambda req: {})
        handler, buf = _make_handler(engine, path="/v1/cloud/routes", body={"route": "GET /del"})
        handler.do_DELETE()
        response = json.loads(buf.getvalue())
        assert response["removed"] is True
        engine.cloud.stop()

    def test_delete_cloud_route_missing_body(self, tmp_path):
        engine = _make_engine_with_cloud(tmp_path)
        handler, buf = _make_handler(engine, path="/v1/cloud/routes")
        handler.do_DELETE()
        assert handler._response_status == HTTPStatus.BAD_REQUEST
        engine.cloud.stop()

    def test_delete_unknown_path_404(self, tmp_path):
        engine = _make_engine_with_cloud(tmp_path)
        handler, buf = _make_handler(engine, path="/v1/cloud/unknown")
        handler.do_DELETE()
        assert handler._response_status == HTTPStatus.NOT_FOUND
        engine.cloud.stop()
