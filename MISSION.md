# YNOT — mission

Give small teams the ability to develop software that becomes more capable through useful work. When a job exposes a missing capability, an agent can build it, test it against checks owned by the host, and make the accepted result available to later jobs.

YNOT is an experimental Orchestra offering built on DSPy. Hyperdrift develops and validates it internally. The ambition is a development system whose capabilities accumulate across tasks, with clear authority, evidence and resource limits.

## Current foundation

The first reference task repairs a schema compatibility failure. A model writes a Python transformation; the host tests it in an isolated interpreter and saves only a passing candidate. A separate process reuses the accepted code on unseen schemas. Revocation prevents subsequent activation. The contract and store are independent of this example and available through `import ynot`.

This establishes a development pattern to extend. It does not establish autonomous discovery of arbitrary skills, a complete API migration product, customer demand or an efficiency advantage. Model-generated code passes finite checks; it does not acquire general correctness by being saved.

## What must earn the extra cost

Compare against a competent direct developer allowed the same models, tools, tests, retries and saved-code reuse. Count acquisition, failed candidates, checking, supervision and later execution. Add workers only when observed evidence justifies different expertise. A single developer can be the right solution.

Our ambitious target is ten times as many independently accepted unseen development tasks for a fixed total inference budget, without more incorrect or unsafe changes. It remains a target. One small demonstration cannot establish that result; the comparison must include current DSPy capabilities and strong direct reuse.

The next useful evidence is transfer across independently chosen development jobs and a second consuming application. Reuse the same contract and executor where they fit; change them when the new job supplies a reason. Do not grow a marketplace, hosted platform or billing system before the work needs one.

## Continuity

Earlier service-selection and development comparisons remain engineering evidence. They found no general benefit from extra orchestration on the bounded tasks tested. The current launch direction is building and reusing capabilities during development.

See [direction](YNOT.md), [the executable foundation](docs/ynot/FOUNDATION.md) and [the continuation record](docs/ynot/HANDOFF.md).
