# The next evaluation: work that fails first time

Designed 3 November 2026 after four bounded jobs, thirty-six live acquisitions and no failed first candidate. The question has not changed: does a host-owned lifecycle of qualified, reusable, revocable capabilities produce more accepted development work per unit of inference than a competent direct developer or plain DSPy with the same reuse rights? What has changed is the understanding that bounded JSON transformations with written rules cannot answer it with a frontier model. This design states what can.

## What the evening established

- The lifecycle, composition and the three-arm harness work and are tested in the real boundary. Mechanism is not the gap.
- Every first candidate from `gpt-6-astra` passed every host case on every job. Repair, evidence retention and supervision were never exercised, so nothing about them was measured.
- Composition was chosen by every arm when the catalogue held exactly the two needed members and the task named both steps. Selection was not tested.
- YNOT's observed contribution is the record and the controls: identity, receipts, revocation, blocked stale members. A direct implementation can build the same; the question is whether having them standard changes outcomes or cost.

## Three things must be true of the next tasks

1. **First candidates fail for a reason the host can state.** A failed case must come back as a reason the arm can act on, so repair is measurable and feedback retention matters.
2. **Reuse is uncertain.** Holdouts must come from a population the model did not write, not from the author's imagination of edge cases.
3. **The catalogue must mislead.** Selection is only tested when picking wrongly is possible and costly.

Three tracks follow, each using the existing executor, store and runner; none needs new infrastructure.

## Track A: real fixtures, hidden tests

Real inputs are messier than specifications. Host cases and holdouts come from records the fleet already holds, and the specification stays as honest and as incomplete as a real brief.

- **Real MCP tool schemas for strict normalisation.** The fleet's own servers define twenty-one tool input schemas (`apps/crunch-accounting-mcp`, `apps/deputy-workforce-mcp`, `apps/traction`). They use `$ref`-free Zod output, nested objects, enums, optional arrays and descriptions that the strict subset must preserve. The host case set is a sample; the holdouts are the rest, unseen. A candidate written to the specification alone will meet shapes the specification never mentioned.
- **Whole OpenAPI documents, not components.** The job becomes "prepare every component schema of this document for a strict client", which needs traversal, `$ref` resolution within the document and the composition of the nullability and strict steps per component. Public documents with open licences supply holdouts. This is a larger programme than one `transform`, with more places to be wrong.
- **Draft-04 in the wild.** Public repositories hold draft-04 schemas written before 2019 with the real mix of keywords. The migration job runs against them with the current `jsonschema` meta-schema as the final host check: output must validate as 2020-12 and must still accept the same instance documents the original accepted. The second check is new and strong: behaviour preserved, not only keywords renamed.

Fixtures are sanitised before entering the repository: names from the fleet's servers are fine, customer data is not. Each job records its source and licence.

## Track B: selection under distractors and stale members

The catalogue is seeded before the run with accepted work that looks useful and is not:

- the **stale strict rule** (required in original property order), which exists as a real earlier contract and fails every current holdout;
- a **near-duplicate** with a plausible name and a subtly different contract version;
- a **wrong-order composition** (strict then nullability) that passes some cases and fails others;
- the correct members under unremarkable names.

Jobs are solvable only by choosing the right members in the right order. Midway through a run the host **revokes** the stale member. For YNOT, activation of any composite using it is blocked and the next attempt must recover; the baselines see the same catalogue with the entry marked withdrawn but nothing enforces it. The measurements are wrong picks, cases failed because of a wrong pick, recoveries after revocation, and whether enforcement prevented a stale reuse that the text alone did not. This is the first place the controls can show value beyond bookkeeping.

## Track C: the model axis

The target is accepted work per fixed inference budget. A frontier model solving bounded jobs first time hides the economics. Every cell therefore runs on two models through the same CLI: `gpt-6-astra` at medium and `gpt-6-luna` at low, the provider's fast and affordable tier. The economic hypothesis worth testing is that a weaker model with accumulated, qualified capabilities and host feedback reaches the frontier model's accepted work at a fraction of the tokens. If it does not, the lifecycle's value is organisational, not economic, and the direction should say so.

## Arms, fairness and measures

Arms stay direct, DSPy and YNOT with equal reuse: same model, prompt, observed failure, specification, catalogue text, allowance of three attempts per job, same executor and host checks, orders reversed, and every cell repeated three times because single runs have already misled once. The DSPy arm may add one optimiser pass over the first jobs so that "current DSPy" means what DSPy actually offers; its acquisition cost counts.

Per job and arm: attempts, model calls, provider tokens, executions, seconds, host cases failed per attempt with reasons, holdout passes, mode (source or composition), wrong picks, recoveries. Per run: accepted holdout cases per thousand output tokens and per model call. A blind review of failed outputs classifies the reason: specification gap, fixture shape, wrong member, carried-over defect.

## Pre-registered reading

- If the weaker model with YNOT matches the frontier model's accepted work at under half the tokens across tracks A and B, the economic claim has a first supporting result and the article can be revised around it.
- If YNOT prevents stale reuse that the baselines commit, the controls have measurable value; publish that specifically and nothing larger.
- If arms remain tied on the weaker model too, retire the orchestration layer from the pitch and keep the store as a library feature.
- Any result on fewer than three repeats per cell is a note, not a finding.

## Budget and order

Track B first: it reuses existing jobs, needs only seeding and a revocation step in the runner, and answers whether the controls do anything. Track A second, starting with the fleet's MCP schemas because the fixtures are already in hand. Track C runs inside both. Rough cost: three tracks, three arms, two models, two orders, three repeats, four to six jobs each, up to three attempts: on the order of six hundred model calls, run in batches with results recorded after each. That is an evening per track at the pace observed tonight, and it is spent only while results keep changing the decision.

Out of scope, as before: hosted customer agents, connection provisioning, wallets, payments and any public claim ahead of the evidence.
