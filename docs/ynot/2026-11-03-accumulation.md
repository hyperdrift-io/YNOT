# Accumulation, composition and a harder job — 3 November 2026

Three arms ran four development jobs in sequence, each keeping what it accepted and receiving a catalogue of that work before the next job. Every arm accepted its first candidate on every job, passed every separately authored holdout, and chose to compose the two earlier capabilities for the fourth job rather than write new code. The job built to fail first time did not fail. The approaches remain indistinguishable on correctness and model use; the difference YNOT makes is in what gets recorded and controlled, not in what gets solved.

## What was added

`CapabilityStore.compose` qualifies an ordered reuse of accepted capabilities under a new contract without generating code; the artefact binds member identities and contract digests, and a revoked or changed member blocks it ([foundation guide](FOUNDATION.md)). Two jobs join the earlier two: [`schema-draft-migration`](../../examples/ynot/migration_case.py), a draft-04 to 2020-12 migration with seven interacting rules and a real `check_schema` rejection as its observed failure, and [`openapi-to-strict`](../../examples/ynot/composed_case.py), whose result is defined as the nullability migration followed by the strict normalisation. The [accumulation runner](../../examples/ynot/capability_accumulation.py) gives every arm the same catalogue and the same right to compose: the store for YNOT, chained saved files for the direct and DSPy baselines.

Twelve holdouts for the two new jobs were written by a separate agent from the specifications alone; its readings of each silence are in the files' notes. All twelve agreed with the controls on first adjudication. The four-job deterministic control runs in the real Deno boundary under test.

## Live results

`gpt-6-astra`, medium reasoning, existing Codex CLI login, at most three candidate attempts per job, same checks, boundary and allowances per arm. The DSPy arm is a plain `dspy.Predict` with source and composition output fields and no optimiser. Jobs ran in the order nullability, strict, migration, composition; arms ran in two orders.

| Arm order | Arm | Attempts (4 jobs) | Model calls | Holdouts | Total seconds | Input / output tokens |
| --- | --- | --- | --- | --- | --- | --- |
| direct → dspy → ynot | Direct | 4 | 4 | 22/22 | 192.944 | 67,719 / 1,791 |
| direct → dspy → ynot | DSPy | 4 | 4 | 22/22 | 171.687 | 69,331 / 1,229 |
| direct → dspy → ynot | YNOT | 4 | 4 | 22/22 | 187.038 | 67,743 / 1,611 |
| ynot → dspy → direct | YNOT | 4 | 4 | 22/22 | 185.666 | 67,231 / 1,630 |
| ynot → dspy → direct | DSPy | 4 | 4 | 22/22 | 171.603 | 69,343 / 1,299 |
| ynot → dspy → direct | Direct | 5 | 5 | 22/22 | 185.700 | 68,282 / 1,617 |

The fourth job, offered a catalogue naming the first two capabilities:

| Arm order | Arm | Attempts | Mode | Output tokens | Holdouts |
| --- | --- | --- | --- | --- | --- |
| direct → dspy → ynot | Direct | 1 | compose | 28 | 6/6 |
| direct → dspy → ynot | DSPy | 1 | compose | 31 | 6/6 |
| direct → dspy → ynot | YNOT | 1 | compose | 28 | 6/6 |
| ynot → dspy → direct | YNOT | 1 | compose | 28 | 6/6 |
| ynot → dspy → direct | DSPy | 1 | compose | 31 | 6/6 |
| ynot → dspy → direct | Direct | 2 | compose | 41 | 6/6 |

The direct arm's extra call in the second order was a provider rejection, "Selected model is at capacity", after two seconds and with no tokens; the retry composed at once. Time includes model generation, qualification, fresh-process reuse and, for the fourth job, two executions per case. Provider token reports are retained as returned; no cash cost is inferred. The DSPy arm again produced shorter outputs; repeated runs would be needed before reading anything into a few seconds.

## What this does and does not show

Composition worked as designed in all six arms: a composed answer costs about thirty output tokens, runs accepted code twice per input, and in YNOT's case produces a composite artefact that later revocation of either member would block. Selection was not tested in a discriminating way: the catalogue held exactly the two needed entries and the task text named both steps. A catalogue with distractors, stale contracts or a wrong order would be the next test of selection.

The migration job, chosen because its rules interact, was solved first time by all three arms in both orders. Across the evening's thirty-six live acquisitions on four jobs, no first candidate failed a host case. These bounded JSON transformations with written rules are below this model's threshold; they cannot measure repair, evidence retention or the value of a supervisor. The honest reading is that YNOT's contribution on such jobs is the record and the controls, which a direct implementation can also build, and that the tenfold target remains untested.

## Decision

Stop adding bounded transformation jobs; they will keep passing first time. The next evaluation needs work whose first candidates fail for reasons a host check can state: larger programmes, specifications with deliberate gaps that require asking, external fixtures the model cannot infer, or tasks drawn from real repository issues with hidden tests. Selection needs a catalogue with distractors and stale members. Keep composition and the accumulation runner; they are the mechanism such a study needs. Nothing here supports publishing an advance.

Public evidence: [accumulation-20261103](evidence/accumulation-20261103/) holds each run's results, catalogues, every candidate, YNOT qualification receipts and the DSPy programme files. Raw provider event streams stay local.
