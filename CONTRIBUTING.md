# Contributing to YNOT

YNOT develops supervised agent work for an Orchestra offering. Read [MISSION.md](MISSION.md) and [YNOT.md](YNOT.md) before changing behaviour. A contribution should make a supported task easier to complete or improve the evidence, authority or resource boundaries it depends on.

Report problems in [this repository](https://github.com/hyperdrift-io/YNOT/issues). Include the YNOT revision, Python version, a minimal reproduction, expected behaviour and the observed result. Remove credentials and private customer data. For a proposed capability, describe the job it would help and the limitation in the current approach. Small fixes can go straight to a pull request here; discuss larger changes before building them.

## Set up

Use a fresh Python environment. YNOT includes its own `dspy` namespace; installing upstream DSPy alongside it can overwrite that engine. See [upstream and attribution](docs/UPSTREAM.md).

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev,deno]'
```

With `uv`, use the committed dependency lock:

```bash
uv sync --locked --extra dev --extra deno
```

## Check a change

Run the affected tests and the focused YNOT suite. The standard suite uses scripted or mocked provider responses and needs no account credentials. Install the `deno` extra to exercise the actual Deno/Pyodide execution checks; a missing runtime is an explicit skip, not a passing sandbox check.

```bash
python -m pytest tests/ynot -q
ruff check ynot examples/ynot tests/ynot
```

For changes to the retained engine, also run its affected tests. CI includes ReAct and custom-engine contract checks, checks the configured internal type scope with `ty check`, and tests the installed wheel outside the checkout. The manual dependency-range workflow exercises the wider non-live engine suite. Passing local controls establishes those contracts; it does not establish live provider quality or a customer outcome.

Keep changes focused and preserve existing authorship, licences and provenance. Tests should reproduce a consequential behaviour, including a failure or stop condition where relevant. Label fictional inputs and scripted responses. Live runs need explicit authority for their access, calls and external effects.

## Submit

Explain the concrete problem, resulting behaviour and verification. State any remaining uncertainty that affects use. Contributors remain responsible for correctness, licensing and understanding their changes, including work assisted by AI.

YNOT maintenance belongs here. A separately reproduced upstream DSPy issue may belong upstream under that project's current contribution policy; do not route a YNOT-specific problem there by default. The [upstream note](docs/UPSTREAM.md) records the relationship and preserved legal notices.
