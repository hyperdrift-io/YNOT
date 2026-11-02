# Retained context and a direct research comparison

Use direct research for a known-service follow-up. In this single live comparison,
supervision produced the same unresolved decision with four extra CLI invocations.
It supplied no demonstrated improvement worth that overhead. This does not settle
whether supervision helps when new evidence requires different expertise.

The code now retains the founder brief and dated trial observations in
`FounderNeed`, passes them through planning and research, and saves them with the
result. Copied inputs prevent a caller from changing the requirements during a
run. Observations cannot satisfy a hard criterion without source evidence.

## The comparison

On 2 November 2026, both paths assessed **Codex CLI** for Orchestra's public
research need. They received the same founder brief, requirements, 30 October
trial observations, access note and official-source domains. The candidate was
already named; this was not a discovery comparison. Direct ran first. Neither
path received the other's output, and neither required a correction or retry.

Both hosts allowed six CLI invocations, 120 seconds per invocation and 300 seconds
overall, with identical CLI default-model settings. YNOT additionally allowed
five supervisor/worker calls and one research callback. Direct called that same
research callback once. Both used the same schema, source checks and deterministic
comparison. The five-web-action request remained a prompt limit, not an enforced
host limit. The exact underlying model identity was not captured.

| Observed result | Direct | Supervised |
| --- | ---: | ---: |
| Decision | `needs_evidence` | `needs_evidence` |
| CLI invocations | 1 | 5 |
| Research callbacks | 1 | 1 |
| Elapsed seconds | 46.227 | 116.719 |
| Web actions | 4 | 5 |
| Reported input tokens | 178,902 | 348,734 |
| Of those, cached input | 132,608 | 242,688 |
| Reported output tokens | 1,002 | 3,428 |
| Reported reasoning output tokens | 51 | 167 |

Elapsed time covers the run, excluding implementation and human/agent review.
Input includes repeated CLI context; cached input is a subset. These figures do
not establish monetary cost, provider-call counts or general performance.

## What the founder gets

Both reports preserve the supplied Orchestra offer and earlier Featurebase
`no_fit` finding without asking for the offer again. Neither recommends adoption.
Both leave research-only enforcement unresolved and ask for current account
conditions. Direct also puts unknown cost in its first three questions.

Both cite the same underlying [official non-interactive documentation](https://learn.chatgpt.com/docs/non-interactive-mode),
independently opened during review. It supports the programme interface, structured
output and session continuation. It does not verify our adapter's complete
execution restrictions or current account allowance. The supervised source URL
redirects to that page. Source-linked research still requires factual review.

The supervisor's stopping explanation calls source links unresolved, although
its accepted ledger marks that criterion as met. The final decision uses the
ledger. This disagreement gives no reason to prefer its added narrative.

## Decision and evidence

Keep the direct path for this follow-up. Retain dynamic supervision as an
experiment for a real job where evidence changes the required expertise; do not
add roles or admission infrastructure to this job. Founder judgement of useful
research, repeatability, private-data suitability and commercial value remain
unestablished.

The 52 focused YNOT tests pass. New checks cover retained context, dated JSON
round trips, copied input ownership and rejection of unsupported factual claims.
Ruff and the copy check pass; separate code review found no remaining blocker.

Raw prompts, events, reports, the frozen input, comparison runner and usage remain
in ignored `local/continuity-20261102/`. The two saved brief hashes match:
`75554d945e62aa81dce68b06a90e78127b2703180d45db0efc7379f20b245627`.
The [handoff](HANDOFF.md) preserves source-chat and checkout provenance.
