"""Trusted execution bridge. Candidate source is sent only into Pyodide."""

import json
import os
import sys

from dspy import PythonInterpreter
from ynot.sandbox import _invalid_constant


def main():
    request = json.load(sys.stdin, parse_constant=_invalid_constant)
    payload = json.dumps(request["payload"], allow_nan=False)
    # The result is data. It is never evaluated as host-side Python.
    program = (
        request["source"]
        + "\nimport json as _ynot_json\n"
        + f"print(_ynot_json.dumps(transform(_ynot_json.loads({payload!r})), allow_nan=False))\n"
    )
    # Populate the trusted runtime's cache without sending it candidate code.
    # npm resolution can fetch even after Deno's import permission is revoked,
    # so candidate execution needs a fresh process with cache-only resolution.
    with PythonInterpreter(sync_files=False) as bootstrap:
        bootstrap.start()
    with PythonInterpreter(sync_files=False) as interpreter:
        interpreter.deno_command[2:2] = ["--cached-only", "--no-prompt"]
        interpreter.start()
        interpreter.execute(
            "import js\n"
            "await js.Deno.permissions.revoke(js.JSON.parse('{\"name\":\"import\"}'))"
        )
        if os.name == "posix":
            import resource

            limit = int(os.environ["YNOT_OUTPUT_LIMIT"])
            # This limits bridge output files, not the already-running Deno
            # process or its pipe buffers. The host bounds time and kills the
            # entire process group; memory is not separately limited.
            resource.setrlimit(resource.RLIMIT_FSIZE, (limit, limit))
        value = interpreter.execute(program)
    result = json.loads(value, parse_constant=_invalid_constant)
    print(json.dumps({"result": result}, allow_nan=False))


if __name__ == "__main__":
    main()
