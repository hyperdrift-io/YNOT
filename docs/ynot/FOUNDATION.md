# Build, qualify and reuse a capability

YNOT's development foundation is an importable lifecycle for executable capabilities. The example makes a model-written schema repair available to a later process. Its contract, execution policy and revocation remain under host control.

```mermaid
flowchart LR
    Job[Development job] --> Candidate[Proposed code]
    Candidate --> Checks[Host acceptance checks]
    Checks -->|Fail| Candidate
    Checks -->|Pass| Store[Saved capability and receipt]
    Later[Later job] --> Activation{Identity, contract and policy valid?}
    Store --> Activation
    Activation -->|Yes| Execute[Bounded execution]
    Activation -->|No or revoked| Block[Refuse activation]
    Owner[Host revocation] --> Store
```

## Run the example

From a source checkout installed with `pip install -e '.[dev,deno]'`:

```bash
python -m examples.ynot.capability_lifecycle --store /tmp/ynot-capabilities
python -m examples.ynot.capability_lifecycle --live --store local/foundation
```

The first command is deterministic: a deliberately faulty candidate fails, a supplied working implementation passes, a fresh process reuses it on four unseen inputs, then a fresh activation is blocked after revocation. This is a lifecycle control, not autonomous model behaviour.

The second command independently asks the same Codex model to solve the task through YNOT and a direct baseline. It uses the existing Codex CLI login and makes real model calls. `--model`, `--reasoning` and `--order ynot-first` are available. Each invocation creates a fresh directory and prints its location. Model requests and usage stay under that directory. Do not publish private inputs from a different task.

The example's inputs are public synthetic reference fixtures. An actual JSON Schema validator first rejects `null` against a valid OpenAPI 3.0 schema. The model sees that failure and the required semantics. It writes a function for the nullability part of an OpenAPI 3.0 to 3.1 migration. This is a real interoperability issue, exercised on bounded fixtures; it is not a complete migration product or evidence of customer demand. [OpenAPI 3.0 semantics](https://spec.openapis.org/oas/v3.0.3.html#schema-object), [OpenAPI 3.1 schema model](https://spec.openapis.org/oas/v3.1.0.html#schema-object).

## The reusable API

```python
from ynot import (
    AcceptanceCase, CapabilityContract, CapabilityStore,
    ExecutionAllowance, PyodideExecutor,
)

# Trusted application code supplies the contract and expected outputs.
contract = CapabilityContract(
    name="my-transform", version="1",
    input_schema={"type": "object"}, output_schema={"type": "object"},
    cases=[AcceptanceCase({"value": 2}, {"value": 3})],
)
executor = PyodideExecutor(timeout=30)
store = CapabilityStore("./capabilities", scope="my-project", executor_policy=executor.policy)
budget = ExecutionAllowance(10)
result = store.qualify(candidate_source, contract, executor, budget)
if result.promoted:
    output = store.run(result.capability_id, {"value": 4}, contract, executor, budget)
    store.revoke(result.capability_id, "Withdrawn by the host")
```

`store.compose([id_a, id_b], contract, executor, budget)` qualifies a reuse of accepted capabilities in order, under a new contract, without new code; see below.

`candidate_source` defines `transform(payload)`. It receives JSON data and returns JSON data. Passing every host case permits promotion; partial or failed qualification does not. Failed attempts and later execution consume the allowance. The core accepts an injected executor so another host can supply a suitable boundary, but its policy identifier must describe that executor honestly.

The store canonicalises every payload, expected value and output as JSON with sorted object keys. A contract therefore cannot depend on object key order; the second consumer below found this when a rule written as "in original property order" passed qualification on alphabetically ordered fixtures and then failed every separately authored holdout on reuse. Order is significant only inside arrays.

Saved identity binds source, contract, scope and execution policy. Every `run` reloads and checks the artefact, contract and revocation. Changing a contract or policy requires qualification under a new identity. Revoking an existing identity cannot be undone by qualifying the same source again. Different projects have separate store scopes. Raw acceptance inputs and expected outputs are not saved in receipts, although generated source can itself contain data and needs appropriate review.

A supervisor may expose qualification and execution as approved tools. The reference uses one developer because this task supplies no reason for more. It does not demonstrate autonomous skill discovery, a specialist switch, automatic capability retrieval or distributed execution. The existing supervisor remains available independently.

## The second consumer

`examples/ynot/strict_schema_case.py` is a different development job on the same lifecycle: normalising a generated JSON Schema for a client that enforces the strict structured-output subset. The observed failure is real and recorded in `examples/ynot/cases/strict-structured-output-observation.json`: on 3 November 2026 the Codex CLI's `--output-schema` request was rejected with HTTP 400 `invalid_json_schema` because `additionalProperties` was not supplied as `false`. The repository's own Codex adapter hand-writes this normalisation for research packets, and MCP tool schemas need the same shape. [OpenAI's strict-mode rules](https://developers.openai.com/api/docs/guides/structured-outputs) are the public source; the contract's rules on `default` and sorted `required` lists are host choices.

The six holdouts in `examples/ynot/cases/strict-structured-output-holdouts.json` were written by a separate agent from the specification alone, without the control implementation, the qualification cases or any repository code, and re-derived by that agent when rule 1 changed. Its reading of the specification's silences is recorded in each pair's `note`. This separates the author of the transfer cases from the author of the prompt and control; it does not make them independent of this organisation or model family.

Run it with `--case strict-structured-output`. Each invocation still creates a fresh store under `--store`; accumulation of several capabilities in one store, and selection among them, is not exercised yet. `--arms direct,dspy,ynot` adds a current-DSPy baseline: a plain `dspy.Predict` on the same Codex engine with host feedback as an input field and the programme saved beside the candidate; no optimiser is run, and its code is reused exactly as the direct arm's.

## Composition: reuse without regeneration

`CapabilityStore.compose(steps, contract, executor, allowance)` qualifies an ordered list of accepted capability identities against a new host contract. No code is generated or saved: the artefact records the member identities and their contract digests under a marker that can never qualify as Python source. Every activation reloads and re-checks each member, so revoking or changing a member blocks the composite, and order is part of the identity. Intermediate values are not validated against member schemas; the composite contract's output schema is. Nested composites run every leaf.

`examples/ynot/capability_accumulation.py` runs several jobs in sequence so each arm's accepted work accumulates: YNOT in one store, the direct and DSPy baselines in one library of saved files. Each job's prompt carries a catalogue of that arm's accepted work by name and task. A candidate is either new source or a composition of catalogue names; the store qualifies a composite, and the baselines chain their saved files through the same executor, so composition is available equally. The fourth job, `openapi-to-strict`, is solvable by composing the first two; the third, `schema-draft-migration`, carries several interacting rules so that first candidates may fail. Deterministic control: `python -m examples.ynot.capability_accumulation --store /tmp/ynot-accumulation`; live: add `--live --arms direct,dspy,ynot`.

## Execution boundary

`PyodideExecutor` sends candidate source into the retained DSPy Deno/Pyodide interpreter, never host-side `exec`. Each call starts a fresh interpreter with no mounted host paths, registered host tools or candidate network/environment permissions. Wall time and captured output are bounded by the host, including process-group cleanup. The runtime may download its interpreter assets during trusted startup.

This executor currently requires POSIX and the optional Deno dependency. Memory is not separately metered. It is not a hardened multi-tenant service. The store assumes a trusted local owner and a single writer. Its checksums detect inconsistency, not malicious replacement by someone who controls the store. Acceptance cases are finite and do not prove general correctness. The existing supervisor's Python callbacks are separate trusted tools, not automatically isolated by this executor.

## Matched comparison

Both live arms receive the same task, observed failure, public contract semantics, pinned model, reasoning setting and at most three candidate attempts. Neither receives acceptance inputs, expected outputs, the supplied control implementation or later reuse fixtures. Candidate code is frozen before later inputs are opened. A candidate can pass first time; no failure or extra specialist is forced.

The direct path uses the same executor and host acceptance cases, saves its passing Python file and reuses it in a fresh process. It receives the same per-case feedback on repair. YNOT uses its standard qualification and activation API. These are matched acquisition and reuse paths, not a contest between a full supervisor and a weaker one-shot baseline. The direct path is bespoke baseline glue; maintenance savings from replacing that glue are not measured here.

Count model calls, provider-reported input/output usage, every attempted execution and wall time through fresh-process reuse. The intentionally faulty candidate and post-run revocation are separate controls. They do not count as competitive safety wins against a direct implementation allowed equivalent controls. Runtime cache warm-up and provider latency can affect timing; do not infer speed from a few runs. No cash price is inferred from subscription token counts.

See [the recorded results](2026-11-02-foundation.md), the [three-arm transfer record](2026-11-03-transfer.md) and the [accumulation record](2026-11-03-accumulation.md). Earlier research and Deputy comparisons remain in the [continuation record](HANDOFF.md).

## Grow the foundation through useful work

The next development should supply a second application and independently authored tasks. Keep generation, qualification and evaluation sets separate. Let each system retain its own accepted code. Include current DSPy programme optimisation, acquisition and repair costs in the baseline, rather than claiming that DSPy only optimises prompts. Vary order, repeat runs and report failed transfer as well as successful reuse.

The ambitious target is ten times as many independently accepted unseen tasks per fixed inference budget, with no increase in incorrect or unsafe changes. An inference-free repeat of a small transformation cannot establish it. Publish total work, correctness and cost, plus an ablation showing what the qualification lifecycle contributes. Add capability selection, contract migration or new execution backends when the next job demonstrates the need; keep the API useful to ordinary development code throughout.
