"""Bounded JSON execution using DSPy's Deno/Pyodide interpreter.

Generated Python runs in WebAssembly, with no mounted host paths, host tools,
environment variables or network permissions. A trusted bootstrap warms runtime
modules before a fresh, cache-only interpreter receives candidate code. This is
not a multi-tenant service.
"""

import json
import math
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path


class SandboxError(RuntimeError):
    """Execution failed or exceeded the configured boundary."""


class PyodideExecutor:
    """Execute ``transform(payload)`` and return one JSON value.

    A fresh interpreter removes candidate state between cases. Wall time and
    bridge output are bounded outside the candidate. A POSIX file-size limit
    bounds the bridge's stdout/stderr files, not Deno's pipe buffers. Memory is
    not separately metered.
    """

    def __init__(self, *, timeout: float = 30, max_bytes: int = 1_048_576):
        if os.name != "posix":
            raise ValueError("This executor requires POSIX process groups")
        if type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("A finite positive timeout is required")
        if type(max_bytes) is not int or max_bytes < 1024:
            raise ValueError("An integer output limit of at least 1024 bytes is required")
        self.timeout, self.max_bytes = timeout, max_bytes
        self.policy = (
            "pyodide-json-v2:no-host-tools,no-mounts,no-env,no-network,cache-only,revoked-imports"
            f":timeout={timeout:g}:max_bytes={max_bytes}"
        )

    def __call__(self, source: str, payload):
        request = json.dumps({"source": source, "payload": payload}, allow_nan=False).encode()
        if len(request) > self.max_bytes:
            raise SandboxError("Input exceeds execution size limit")
        environment = {k: v for k, v in os.environ.items() if k in {"PATH", "HOME", "TMPDIR", "SYSTEMROOT", "LANG"}}
        # Select this installed/source package without inheriting arbitrary PYTHONPATH.
        environment["PYTHONPATH"] = str(Path(__file__).resolve().parent.parent)
        environment["YNOT_OUTPUT_LIMIT"] = str(self.max_bytes)
        with tempfile.TemporaryDirectory(prefix="ynot-execution-") as folder:
            base = Path(folder)
            (base / "request.json").write_bytes(request)
            with (base / "request.json").open("rb") as stdin, (base / "stdout").open("wb") as stdout, (
                base / "stderr"
            ).open("wb") as stderr:
                process = subprocess.Popen(
                    [sys.executable, "-m", "ynot._sandbox_worker"],
                    stdin=stdin,
                    stdout=stdout,
                    stderr=stderr,
                    cwd=folder,
                    env=environment,
                    start_new_session=True,
                )
                deadline = time.monotonic() + self.timeout
                failure = None
                try:
                    while process.poll() is None:
                        if time.monotonic() >= deadline:
                            failure = "Execution timed out"
                            break
                        if any((base / name).stat().st_size >= self.max_bytes for name in ("stdout", "stderr")):
                            failure = "Execution output exceeds size limit"
                            break
                        time.sleep(0.02)
                finally:
                    # Kill descendants too: terminating the wrapper alone leaves Deno running.
                    self._kill(process)
                    process.wait()
                if failure:
                    raise SandboxError(failure)
            output = (base / "stdout").read_bytes()
            if len(output) >= self.max_bytes:
                raise SandboxError("Execution output exceeds size limit")
            if process.returncode:
                detail = (base / "stderr").read_text(errors="replace")[-2000:]
                raise SandboxError(f"Execution failed ({process.returncode}): {detail}")
            try:
                result = json.loads(output, parse_constant=_invalid_constant)
            except (ValueError, UnicodeError) as exc:
                raise SandboxError("Execution did not return a JSON result") from exc
            if not isinstance(result, dict) or set(result) != {"result"}:
                raise SandboxError("Invalid execution envelope")
            return result["result"]

    @staticmethod
    def _kill(process):
        try:
            if os.name == "posix":
                os.killpg(process.pid, signal.SIGKILL)
            else:
                process.kill()
        except ProcessLookupError:
            pass


def _invalid_constant(value):
    raise ValueError(f"Non-finite JSON value: {value}")
