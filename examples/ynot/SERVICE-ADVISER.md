# Find a service that fits the actual need

This first application connects a founder's outcome and hard requirements to source-linked service evidence and a reversible trial. It complements the services being assessed. The output is the best fit among the reviewed candidates and stated requirements, with uncertainty visible.

## Run it

From the checkout root:

```bash
PYTHONPATH=. python -m examples.ynot.service_adviser --demo
```

The demonstration creates and executes two real DSPy ReAct specialists during one mission. Scripted responses first investigate a service and then configure a specialist to inspect a restricted alternative. Findings pass forward through the existing supervisor checkpoint. The services, sources and responses are fictional. The run demonstrates mechanics, not intelligent discovery, live research or recommendation quality.

Use `--json` for the full decision record, findings, sources and execution trace. A caller can compare an evidence packet without any model calls:

```bash
PYTHONPATH=. python -m examples.ynot.service_adviser --case examples/ynot/cases/orchestra-research-services.json
```

The included real case compares Apollo, Clay and Exa against Orchestra's public-research need using seven official sources checked on 30 October 2026. Budget, account access and data-handling requirements remain unresolved. It suggests Exa as a conditional trial among the reviewed interfaces; this is neither a global vendor ranking nor proof of live service quality. The case is a saved documentation review and makes no model or provider calls. Inspect current sources again before adopting or paying for a service.

A case contains `need`, `sources` and `assessments`, matching the Pydantic records in `service_adviser.py`. Alternatively supply `--brief need.json --evidence evidence.json`. This path evaluates saved evidence; it does not run agents or refresh a market survey. The printed brief is deliberately shorter than the complete JSON record.

The need can include `founder_brief` and `trial_observations`. Each observation carries a `summary`, `observed_at` date and `evidence_ref`. These preserve the actual job and earlier trial findings through planning and research. They are context, not vendor-source evidence, and cannot satisfy a criterion or change the permitted actions. The report retains the full `founder_need`; the live adapter also writes `founder-need.json` for the next step. Pass that file as the next run's brief, revising requirements only when the founder's job changes. Existing briefs remain valid.

For a live run, construct `ServiceAdviser(planner_lm, {"research": worker_lm}, approved_research_callback)` and pass a `FounderNeed`. The callback receives a service and research question and returns an `EvidencePacket`. It is caller-approved code, not sandboxed by this example. Reuse a narrow service API where it supplies the capability. Credentials, account access, provider costs and downstream actions remain the caller's responsibility; this example activates none of them.

## Use an existing Codex CLI login

The optional [live adapter](live_codex.py) runs the planner and research through Codex CLI. It uses the CLI's existing authentication and CLI default model; it never reads credentials or opens an account.

```bash
PYTHONPATH=. python -m examples.ynot.live_codex \
  --brief need.json --output-dir /tmp/ynot-live-run \
  --domains developers.openai.com,learn.chatgpt.com,exa.ai \
  --access-note "Codex available; other vendor access unconfirmed."
```

Supply official domains relevant to the need. The inference processes have tools disabled; research processes receive public-web search. Both use a read-only sandbox, no shell, apps, hooks or subagents, and ignore user configuration. This is a local demonstration adapter, not public-agent admission.

For a known candidate, add `--direct-service "Codex CLI"` to call the same research adapter and deterministic comparison without supervisor/worker inference. Use the same brief, domains, access note and host limits in both paths. This baseline tests whether supervision adds value to that follow-up; it does not compare market discovery. Keep each output in a new directory and preserve failures as well as successes.

The host limits the run to 24 CLI invocations, 120 seconds per invocation and 12 minutes overall. DSPy separately limits supervisor/worker calls and research callbacks. Web-action limits are prompted, not enforced inside the CLI. Token usage includes repeated CLI startup context; completed CLI turns do not reveal every underlying provider call or retry. These controls do not cap monetary charges.

The output directory retains prompts, JSONL events, research packets, usage and the decision. `research-packets.json` records callback output; the report's sources and rejected evidence show what the ledger accepted. A timeout preserves partial public events. Stderr is excluded. Use public inputs only. Source URLs must appear as explicit attempted-open targets or page-result URLs within an open action, and belong to the approved domains. Every evidence service label must exactly match the requested service; aliases are rejected. This proves an attempted page action, not successful retrieval or factual truth; inspect the source content before acting on its claims.

## First live observation

An internal Orchestra run on 30 October 2026 used the existing ChatGPT-authenticated Codex CLI. The first selection exhausted its tool allowance after invalid duplicate findings and inconsistent service labels. The ledger retained uncertainty. The corrected run completed with one specialist, four supervisor/worker inference invocations and one live research invocation, returning a conditional Codex trial.

A separate public-research trial also completed with one dynamically configured specialist and a no-fit decision: existing capabilities weakened the proposed opportunity. The host supplied the briefs, chose the exercised capability for that trial after the first selection stalled, checked the sources independently and launched the corrected selection with those observations. This was supervised live work, not one unattended selection-to-execution transaction.

The run exposed missing context between selection and execution and substantial repeated-context usage. It established no matched baseline, qualified lead, client result, commercial adoption or advantage over upstream DSPy. The [2 November comparison](../../docs/ynot/2026-11-02-comparison.md) tests the subsequent context fix: both paths retained the offer, while the direct path reached the same unresolved decision with fewer invocations. Keep direct research for this known-service follow-up. The [continuation record](../../docs/ynot/HANDOFF.md) owns the next decision.

## What decides the recommendation

The model configures and runs research specialists. A host-owned ledger deep-copies accepted research callback results, so a later change to a callback’s cached model instance cannot rewrite earlier evidence. Worker prose cannot turn a missing or mismatched source into accepted evidence.

Every factual verdict must cite an existing source for the same service and criterion. Unknown or missing hard requirements prevent an unconditional trial recommendation; a known failed requirement excludes the service. A declared budget also requires a sourced cost in the same currency. Unknown price is never treated as zero. Sources use immutable evidence-snapshot IDs: new content or check dates require a new ID. Later dated evidence can revise a finding; contradictory findings at the latest checked date remain unresolved even when one assertion is repeated. An older price cannot overwrite a newer price. A newer check date supplies an ordering rule, not proof that the claim is true. Earlier account/setup uncertainties remain visible across research steps.

One eligible service may be suggested for a reversible trial. Outstanding access, cost or other uncertainties make that trial conditional. Several eligible services produce a clarification about the trade-off rather than an invented weighted ranking. No supported candidate produces `no_fit`; insufficient evidence produces `needs_evidence`. A trial suggestion is not a purchase recommendation.

A source link establishes attribution, not factual truth. The supplied facts still need current primary-source inspection, representative trials and founder judgement. The application does not verify vendor performance, completeness of market discovery, account permissions, price accuracy or legal suitability. Date fields describe the submitted evidence; they do not refresh it.

The inherited runtime enforces model/tool call counts and approved tool/model names. It does not enforce monetary, token or wall-time limits, prove reviewer independence or provide public wallet admission. The host-owned ledger and runtime are synchronous and should not be shared across concurrent missions.

## Reusable capability discovered

The requirement-to-evidence contract is a useful enabler: unknown evidence remains unknown, and a model's positive narrative cannot waive a failed constraint. A later provider or execution-runtime selector could use the same contract. That is a reuse hypothesis; this implementation keeps it inside the service adviser until another real consumer establishes what should be shared.

Run the focused checks:

```bash
PYTHONPATH=. python -m pytest tests/ynot/test_service_adviser.py tests/ynot/test_runtime_specialists.py -q
```

For a comparison, pin `--model` and `--reasoning-effort` on both live CLI paths.
The host records the requested settings; omission retains the CLI defaults.
Requested settings do not prove the provider’s resolved model revision.
