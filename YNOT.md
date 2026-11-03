# YNOT direction

Useful development work should leave the system with capabilities it can use again. YNOT turns a proposed capability into an executable, checked and revocable artefact. The host owns what passing means, what the code may access and when it may run.

Yann selected **build and reuse capabilities during development** on 2 November 2026. This supersedes the prospect-specific launch direction. YNOT is an Orchestra offering; Hyperdrift is its developer and internal validator, not a customer.

## Implemented foundation

The `ynot` package contains the existing mission supervisor and a reusable capability lifecycle. The supervisor can configure DSPy workers from approved model and tool registries. The new host API qualifies executable Python, saves an immutable identity tied to its contract and execution policy, checks that identity on reuse, and honours revocation.

The reference example repairs OpenAPI nullability for a JSON Schema consumer. It includes a labelled bad-candidate control and an optional matched live comparison. Each accepted implementation runs on unseen inputs in a fresh process. The direct baseline can also save and reuse its code; zero later model calls alone is not a YNOT advantage.

A second development job, normalising a generated JSON Schema for a strict structured-output client, uses the same lifecycle with a different contract. Its holdout cases were authored separately from the prompt and control, and a current-DSPy baseline runs beside the direct one. Building it exposed that contracts cannot depend on JSON object key order, because the store canonicalises values; the [foundation guide](docs/ynot/FOUNDATION.md) records the rule and the [transfer record](docs/ynot/2026-11-03-transfer.md) the results.

The [foundation guide](docs/ynot/FOUNDATION.md) owns the API, reproducible commands, experiment and limits. The Orchestra launch article is being prepared separately for review.

## The advance to pursue

The intended advance is cumulative capability: useful work expands what later jobs can execute reliably, while the mission's authority remains with the host. A new prompt or a saved code string alone does not deliver that. Qualification, provenance, activation, scoped access, cost and withdrawal all matter.

This is not a claim to have invented executable learning or dynamic orchestration. [DSPy Flex](https://dspy.ai/current/diving-deeper/flex/) evolves whole module code; [Voyager](https://arxiv.org/abs/2305.16291) introduced a growing executable skill library; [DGM](https://sakana.ai/dgm/) explores tested agent self-modification. [Deep Agents](https://docs.langchain.com/oss/python/deepagents/dynamic-subagents) documents dynamic delegation. YNOT must earn its place through a useful implementation and measured outcomes alongside that work.

Tenfold improvement is a research target: independently accepted unseen development work per fixed total inference budget, including acquisition and checking. It is not a launch result. Test against current DSPy and a competent direct developer with equal reuse rights. Publish failures and retire orchestration that adds no useful outcome.

## Boundaries and next development

The store is local and single-writer, with a trusted owner. Hashes detect inconsistent artefacts; they do not protect against an attacker who controls the store. The supplied executor runs candidate code in DSPy's Deno/Pyodide interpreter with bounded wall time and output. It does not separately meter memory or supply a multi-tenant service. The supervisor's existing registered Python tools remain trusted callbacks outside that executor.

The second consumer exists; both bounded jobs were solved first time by every arm, so they no longer tell the approaches apart. The next jobs need failing first candidates and uncertain transfer. Then evaluate accumulation of several capabilities in one store, selection among them, stale contracts and repair after failed transfer. This is how the foundation grows beyond demonstrations. Hosted customer agents, connection provisioning, distributed scheduling, wallets and payments remain outside the current implementation.

## Earlier evidence

The [initial live comparison](docs/ynot/2026-11-02-comparison.md), [stopping correction](docs/ynot/2026-11-02-stopping.md) and [Deputy comparison](docs/ynot/2026-11-02-deputy.md) remain relevant. Retaining termination reasons, source observations and remaining allowances fixed an early-stop defect. The broader cases found no material general quality advantage, and the Deputy case was a practical tie. More specialists are not an objective.

The service adviser remains available as an earlier application. Apollo permission boundaries still apply to any future integration; no live Apollo connection, prospect contact or public participation service has been activated by this foundation work.
