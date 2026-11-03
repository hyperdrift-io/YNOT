import importlib.util
import json
import shutil
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import quote
from uuid import uuid4

import pytest

from ynot.sandbox import PyodideExecutor, SandboxError

pytestmark = pytest.mark.skipif(
    not (shutil.which("deno") or importlib.util.find_spec("deno")),
    reason="The optional Deno runtime is required; CI installs .[deno]",
)


@pytest.mark.parametrize("timeout", [float("nan"), float("inf"), 0, -1, True, "30"])
def test_timeout_must_be_finite_and_positive(timeout):
    with pytest.raises(ValueError):
        PyodideExecutor(timeout=timeout)


@pytest.mark.parametrize("max_bytes", [float("inf"), 1024.0, 1023, True])
def test_output_limit_must_be_a_bounded_integer(max_bytes):
    with pytest.raises(ValueError):
        PyodideExecutor(max_bytes=max_bytes)


def test_json_execution_and_fresh_state():
    execute = PyodideExecutor(timeout=45)
    source = "seen = []\ndef transform(payload):\n    seen.append(payload)\n    return seen"
    assert execute(source, {"value": 3}) == [{"value": 3}]
    assert execute(source, {"value": 4}) == [{"value": 4}]


def test_host_environment_and_files_are_not_available(tmp_path, monkeypatch):
    sentinel = tmp_path / "private.txt"
    sentinel.write_text("not-for-candidate")
    monkeypatch.setenv("YNOT_PRIVATE_SENTINEL", "not-for-candidate")
    source = """
def transform(payload):
    import os
    try:
        text = open(payload['path']).read()
    except OSError:
        text = None
    return {'env': os.environ.get('YNOT_PRIVATE_SENTINEL'), 'file': text}
"""
    assert PyodideExecutor(timeout=45)(source, {"path": str(sentinel)}) == {"env": None, "file": None}


def test_timeout_kills_generated_loop():
    with pytest.raises(SandboxError, match="timed out"):
        PyodideExecutor(timeout=3)("def transform(payload):\n    while True: pass", None)


def test_output_limit_is_enforced():
    with pytest.raises(SandboxError):
        PyodideExecutor(timeout=45, max_bytes=4096)("def transform(payload):\n    return 'x' * 10000", None)


def test_invalid_result_is_not_executed_in_host():
    with pytest.raises(SandboxError):
        PyodideExecutor(timeout=45)("def transform(payload):\n    return float('nan')", None)


def test_candidate_fetch_cannot_reach_loopback():
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            requests.append(self.path)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"host-only")

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}/private"
    expression = (
        "(async () => { try { await fetch("
        + json.dumps(url)
        + "); return 'allowed'; } catch (e) { return e.name + ':' + e.message; } })()"
    )
    source = f"import js\noutcome = await js.eval({expression!r})\ndef transform(payload):\n    return str(outcome)\n"
    try:
        result = PyodideExecutor(timeout=45)(source, None)
        assert "Requires net access" in result
        assert requests == []
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_worker_loaders_cannot_fetch_remote_modules_or_npm_metadata():
    # Deno's Worker loader used to reach these default module hosts even though
    # ordinary fetch and direct js.eval imports were blocked. Unique targets
    # also prevent a cached package or earlier 404 masking registry access.
    nonce = uuid4().hex
    targets = [f"https://deno.land/ynot-denied-{nonce}.js", f"npm:ynot-denied-{nonce}"]
    worker_source = (
        "await Deno.permissions.request({name:'import', host:'deno.land'}); "
        "const results = []; for (const target of "
        + json.dumps(targets)
        + ") { try { await import(target); results.push('allowed'); } "
        "catch (e) { results.push(e.name + ':' + e.message); } } "
        "postMessage(JSON.stringify(results));"
    )
    worker_url = "data:application/javascript," + quote(worker_source)
    expression = (
        "new Promise(resolve => { const w = new Worker("
        + json.dumps(worker_url)
        + ", {type:'module'}); w.onmessage = e => { w.terminate(); resolve(e.data); }; "
        "w.onerror = e => { w.terminate(); resolve(JSON.stringify([e.message])); }; })"
    )
    source = (
        f"import js, json\noutcome = await js.eval({expression!r})\n"
        "def transform(payload):\n    return json.loads(str(outcome))\n"
    )
    result = PyodideExecutor(timeout=45)(source, None)
    assert len(result) == 2
    assert "Requires import access" in result[0]
    assert "not found in cache" in result[1] and "--cached-only" in result[1]
