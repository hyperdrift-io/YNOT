# YNOT continuation — development foundation

## Taken over on 3 November 2026

Checkpoint `ynot-transfer-20261103`. Claude Code session
`2399db7a-ef20-498c-a958-8ad202bc99c7` (desktop title “YNOT thread continuation”,
`claude --resume` with that ID) took over from Codex chat **Continue YNOT thread**
(`codex://threads/01a19d95-055f-7713-96a6-58e04eef59f8`, working turns 2 November
18:45–23:46 UTC). That chat's record is historical; its last outcome is the
foundation commit `5675159` below. Earlier source:
`01a0f4cc-babe-7093-9c22-5be57b45f70e`.

State read at the takeover: this checkout is `main` at `5675159`, clean and equal
to `origin/main`; GitHub run 41547358725 succeeded on that commit. The temporary
worktree `apps/.worktrees/ynot-foundation-20261102` and its local branch were
removed because they held nothing beyond main. `tests/ynot` passed tonight: 114
tests in 56 s on Python 3.12 using the interpreter at
`/Users/yannvr/Documents/ChatGPT/OSS/work/dspy-10656/.venv` with `PYTHONPATH=.`;
this checkout has no environment of its own. The launch article draft passes the
mechanical HD copy check and still awaits Yann's editorial review; nothing is
published.

Traction: preparation `586e7a88b3534ab694e6e6ed3e655cac` is completed. The
follow-on preparation is `orchestra-ecosystem-trust/6dd856ba4fe14b17875c891538a5858e`,
accepted and bound to the Claude session above.

Done on 3 November: the second consumer, strict structured-output schema
normalisation, runs on the same lifecycle (`--case strict-structured-output`)
with a recorded real client rejection, seven host cases and six holdouts written
by a separate agent from the specification alone. The harness gained a
current-DSPy arm (`--arms direct,dspy,ynot`). The real boundary exposed that
contracts cannot depend on JSON object key order because the store canonicalises
values; the rule was amended and the holdouts re-derived independently. Live
three-arm runs on both jobs: every arm accepted its first candidate and passed
every holdout with one model call, so neither job discriminates between the
approaches. [Transfer record](2026-11-03-transfer.md), evidence under
`evidence/transfer-20261103/`. Preparation `6dd856ba4fe14b17875c891538a5858e`
carries a checkpoint and is completed with this landing.

Next: jobs where first candidates fail and transfer is uncertain, run across the
same three arms with equal reuse; exercise accumulation of several capabilities
in one store, selection among them and repair after failed transfer. The article
still waits for Yann's review. No 10x claim or publication.

## Earlier work — 2 November 2026

Checkpoint `ynot-continuity-20261102`. Taken over by Codex chat
`01a19d95-055f-7713-96a6-58e04eef59f8` from **Plan Orchestra OSS contributions**
(`01a0f4cc-babe-7093-9c22-5be57b45f70e`). The YNOT decisions and implementation
were made on 30 October; later turns in that source concern OSS follow-through.
YNOT work continues in the new chat; the existing OSS routine retains its source.

## Scope and evidence

The [mission](../../MISSION.md) is selecting a service for the founder's actual
need. [YNOT.md](../../YNOT.md) owns direction and the
[service guide](../../examples/ynot/SERVICE-ADVISER.md) owns the runnable example.
The first live run completed with a no-fit prospect finding and a separate
conditional service trial. Its coordinator supplied context between runs.
There was no matched direct-workflow baseline or customer outcome.

The context fix and [live comparison](2026-11-02-comparison.md) are complete.
Both paths retained the supplied offer and returned `needs_evidence`. Direct
research used one invocation and 46.227 seconds; supervision used five and
116.719 seconds. Keep the direct path for a known-service follow-up. A later private founder case exposed an early-stop defect. The
[completion correction and broader comparison](2026-11-02-stopping.md) retain
actual worker termination and source observations, allow bounded continuation,
and test the original regression plus two independently prepared cases. The
correction recovered a specific lead in the regression; the independent cases
showed no material quality advantage. No general superiority or commercial
result has been established.

Base: YNOT `origin/main` at `879366b02258ecb89f71295a84d0fbb417a9578b`, fetched
2 November. Main and the two older implementation worktrees were clean; both
older branches predate main and remain intact. Machine-specific checkout paths,
raw evidence and reproduction details are in the ignored `local/` directory.

Traction work: `orchestra-ecosystem-trust/ecc78494af664b24add90b60370a6164`, linked
to the existing `ynot-service-comparison` roadmap task. Native session bound.
No prospect contact, purchase, article publication or deployment is included.
The existing article plan remains review-held; wallet admission follows a
concrete need for external participation.

The stopping correction preparation is complete:
`orchestra-ecosystem-trust/7c13d04ab4c541ff8367a8d4cbe4c912`.

The [real Deputy pilot comparison](2026-11-02-deputy.md) extends the test beyond
service research. Both approaches narrowed the existing offer after inspecting
and probing its implementation. Blind review found a practical tie. YNOT ran
one additional summer-time probe, used one worker which explicitly finished,
and made no replacement or continuation. It took 13 calls and 262 seconds;
direct took 12 and 237, while using more input tokens. The extra reproduction
did not change the pilot decision. This is preparation
`orchestra/ae76bb01c0b74db2a09960c19f5ff775`.

Use direct investigation for the bounded tasks tested. Crossing subject areas
does not itself justify a new worker. A future supervised trial needs an
observed capability or handoff the active worker cannot adequately supply;
neither additional workers nor using the full allowance is an objective. The
Deputy pilot decision and unsent operator draft are in
`local/deputy-eval-20261102/PILOT-DECISION.md`; actual operator validation remains
outstanding. Yann subsequently rejected Deputy as a commercial example because
it had no traction. Retain the comparison as engineering evidence and stop
using its pilot draft as the proposed prospect offer.

The earlier commercial hypothesis
is configuring and provisioning agents for a SaaS customer's actual job. The
prototype's bounded worker configuration is implemented; persistent deployment,
scoped connection provisioning and lifecycle operation remain proposed. Confirm
a prospect-relevant workflow before expanding the platform. No new build,
customer commitment or contact has been authorised by this discussion. Private
case records and reproduction files remain in the owning checkout's ignored
`local/`.
