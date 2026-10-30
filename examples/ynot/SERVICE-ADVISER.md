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
PYTHONPATH=. python -m examples.ynot.service_adviser --case case.json
```

A case contains `need`, `sources` and `assessments`, matching the Pydantic records in `service_adviser.py`. Alternatively supply `--brief need.json --evidence evidence.json`. This path evaluates saved evidence; it does not run agents or refresh a market survey. The printed brief is deliberately shorter than the complete JSON record.

For a live run, construct `ServiceAdviser(planner_lm, {"research": worker_lm}, approved_research_callback)` and pass a `FounderNeed`. The callback receives a service and research question and returns an `EvidencePacket`. It is caller-approved code, not sandboxed by this example. Reuse a narrow service API where it supplies the capability. Credentials, account access, provider costs and downstream actions remain the caller's responsibility; this example activates none of them.

## What decides the recommendation

The model configures and runs research specialists. A host-owned ledger records approved research callback results. Worker prose cannot turn a missing or mismatched source into accepted evidence.

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
