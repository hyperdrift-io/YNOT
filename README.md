# YNOT

YNOT lets development agents build, qualify and reuse executable capabilities. A job can leave behind tested code that later jobs can use, under checks and permissions owned by the host.

This is an experimental [Orchestra](https://orchestra.hyperdrift.io/) offering, developed and internally validated by Hyperdrift. The foundation example repairs an API schema compatibility failure, saves a passing implementation and reuses it on unseen inputs in a fresh process.

## What works today

- A host-owned contract checks generated Python in a Deno/Pyodide interpreter. Passing code receives an identity tied to its source, contract, scope and execution policy.
- A local store validates that identity on reuse and blocks revoked capabilities. Candidate code cannot rewrite the host's acceptance checks.
- Two development jobs use the same lifecycle: repairing OpenAPI nullability for a JSON Schema consumer, and normalising a generated schema for a strict structured-output client. The second job's holdout cases were written separately from its prompt and control.
- A supervisor creates and executes DSPy ReAct workers from approved model and tool registries when the job needs them.
- The host validates worker configurations and enforces model-call and tool-call allowances. Findings, tool observations and stopping reasons remain inspectable.
- The service adviser checks supplied evidence against requirements. Its examples support scripted controls, saved sources and an optional Codex research integration.

The foundation is experimental. Its capability executor bounds time and output but does not separately meter memory. The store assumes a trusted local owner and one writer. Existing registered supervisor tools remain trusted Python callbacks. Persistent hosted customer agents and connection provisioning remain proposed work. Internal comparisons do not establish customer demand or a general quality or cost advantage.

Read the [mission](MISSION.md), [direction and evidence](YNOT.md), and [continuation record](docs/ynot/HANDOFF.md) for the current boundaries and next step.

## Run locally

Use a fresh Python environment. The distribution is named `ynot-ai`; it includes the retained `dspy` engine namespace, so do not install a separate DSPy distribution in the same environment. These instructions install this checkout; there is no package-publication workflow.

```bash
git clone https://github.com/hyperdrift-io/YNOT.git
cd YNOT
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev,deno]'
python -m examples.ynot.capability_lifecycle --store /tmp/ynot-capabilities
```

The default demonstration rejects a faulty candidate, qualifies a working one, reuses it in a new process and verifies revocation. It is a deterministic control. `--case strict-structured-output` runs the second job. Add `--live` for independent runs through Codex using your existing login, and `--arms direct,dspy,ynot` to include a plain current-DSPy baseline; every arm can test, save and reuse code. This makes real model calls. Run examples from the checkout because they are not included in the wheel. The executor currently requires a POSIX host and the optional Deno runtime; first use may download its interpreter assets.

The earlier [runtime example](examples/ynot/README.md) and [service adviser guide](examples/ynot/SERVICE-ADVISER.md) remain available, with their scripted inputs and live-research limits stated separately.

The reusable API starts with `from ynot import CapabilityContract, CapabilityStore, PyodideExecutor`. The [foundation guide](docs/ynot/FOUNDATION.md) covers the full lifecycle and comparison. `Supervisor`, `Allowance` and `WorkerSpec` are also public; existing example imports remain compatible.

## Develop and contribute

Run the focused offline checks from the checkout:

```bash
python -m pytest tests/ynot -q
ruff check ynot examples/ynot tests/ynot
```

[Contributing](CONTRIBUTING.md) covers setup, validation and reporting a problem. Use [YNOT issues](https://github.com/hyperdrift-io/YNOT/issues) for this repository.

## Built on DSPy

YNOT retains DSPy's engine and Git history. The original MIT licence and Stanford Future Data Systems copyright remain in [LICENSE](LICENSE). [Upstream and attribution](docs/UPSTREAM.md) explains the package boundary, bundled components and retained compatibility checks. DSPy documentation describes the upstream framework; it is not YNOT product documentation.
