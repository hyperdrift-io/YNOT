# YNOT development foundation — 2 November 2026

The reusable capability lifecycle works on the reference task. A model-generated transformation passed host-owned checks, survived a process boundary, ran on unseen inputs and was blocked after revocation. The direct baseline also generated and reused a correct implementation. No quality, inference-cost or speed advantage was demonstrated.

## Corrected-policy live results

All four runs used `gpt-6-astra`, medium reasoning, through the existing Codex CLI adapter. The two pairs reverse execution order. Each arm had at most three candidate attempts and access to the same checks and execution boundary. Every arm succeeded on its first candidate.

| Pair and order | Approach | Qualification | Unseen reuse | Model calls: acquisition / reuse | Executions | Total seconds | Input / output tokens |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1: direct first | Direct | 7/7 | 4/4 | 1 / 0 | 11 | 33.633 | 16,708 / 395 |
| 1: direct first | YNOT | 7/7 | 4/4 | 1 / 0 | 11 | 37.785 | 16,714 / 423 |
| 2: YNOT first | YNOT | 7/7 | 4/4 | 1 / 0 | 11 | 43.979 | 16,711 / 355 |
| 2: YNOT first | Direct | 7/7 | 4/4 | 1 / 0 | 11 | 40.925 | 16,705 / 406 |

Time includes model generation, qualification and reuse in a fresh process. The separate revocation control follows that interval. Provider token reports are retained as returned, including separate reasoning and cache fields; no cash cost is inferred from a subscription run. The application prompts have identical hashes within each pair. Provider input totals differ slightly despite identical application prompts.

YNOT was slower in both pairs. Two small pairs cannot quantify a general overhead or establish equivalence, but they provide no reason to prefer YNOT for this transformation on output quality or inference use. The direct path remains a valid simple solution.

The comparison tests the same code-generation task through a standard capability lifecycle and bespoke direct test-and-reuse code. It does not test autonomous capability discovery, a specialist switch, a full supervisor or DSPy optimisation. Neither extra workers nor extra failed attempts were forced.

## What YNOT adds here

The host saves a qualification receipt and a source identity tied to the contract, project scope and execution policy. A later process can activate the capability through the same API; changed identity, contract or policy is rejected. The host can withdraw an accepted identity, and revocation is checked on every activation.

These controls are independently tested, not judged by the generating model. A direct implementation can supply equivalent controls. This experiment does not measure maintenance effort, incident reduction or commercial value from standardising them.

The public evidence includes [results and usage](evidence/foundation-20261102/results.json), exact generated sources and qualification receipts in the same directory. Raw provider event streams remain local. The [guide](FOUNDATION.md) describes reproduction and the public contract. The seven qualification inputs and four later fixtures are disjoint but small and authored for this example. They establish bounded behaviour, not broad transfer or customer demand.

## Controls and a defect found before landing

The deterministic control deliberately submits an identity function that fails qualification, then a supplied correct implementation. It exercises rejection, promotion, fresh-process reuse and revocation. It is labelled scripted and contributes no evidence about model planning. Its receipt is saved beside the live results.

Independent review found that the first executor boundary blocked ordinary network requests but allowed Deno Worker module loading. Those first two live pairs are retained in the results as superseded evidence. Their code was functionally correct, but their execution policy did not enforce the intended boundary.

The corrected executor warms trusted runtime modules without candidate code, starts a fresh cache-only interpreter, disables permission prompts and revokes module-import permission before sending the candidate. Regression checks cover ordinary fetch, Worker HTTPS imports, npm metadata resolution and an attempt to regain import permission. Its policy is `pyodide-json-v2`; an earlier identity cannot silently activate under it. All live numbers in the table were rerun under this corrected policy. Eight model calls were used across the preliminary and corrected experiments, four in each group.

Core checks cover altered source and receipts, changed contracts and scope, revocation across reload, failed and partial qualification, preservation of earlier capabilities, immutable acceptance snapshots, exact JSON comparison, failed atomic replacement, and refusal to retrieve remote validation schemas. The reference harness also retains failed acquisitions and reuse attempts, and runs the independent other arm after failure.

Local validation passed on Python 3.10.22 and 3.12.14: 283 tests passed and one optional ReAct-extra test was skipped on each. A fresh wheel installed outside the checkout passed 22 checks, including actual candidate execution and the network/module-loader restrictions. Ruff, configured types, dependency consistency, lock and workflow checks passed. These are local results; the GitHub workflow reports its own Linux result after push.

## Decision

Keep the reusable API and the bounded reference as a development foundation. Use a second real consumer and independently prepared transfer tasks to decide the next abstraction. Leave the launch article under review. An order-of-magnitude gain remains a target requiring a substantially broader evaluation, with current DSPy and direct systems allowed equal code reuse and all acquisition costs counted.
