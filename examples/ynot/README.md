# Specialists configured during a run

The [service adviser](SERVICE-ADVISER.md) applies this runtime to a founder’s requirements and source-linked service evidence. It provides a short decision brief, JSON output and a reversible-trial recommendation.

Run the runtime control from the checkout root:

```bash
PYTHONPATH=. python -m examples.ynot.runtime_specialists
```

The demonstration uses real DSPy Predict and ReAct execution with scripted DummyLM responses and fictional source material. It makes no provider calls and finds no real customer. It demonstrates the execution contract, not intelligent selection, improved prospect quality or an advantage over upstream DSPy.

A supervisor starts with no worker instances. Its next-step programme receives the mission, retained findings, approved capabilities and remaining allowance. It generates a `WorkerSpec`: the evidence gap, purpose, instructions, model alias, selected tools, output contract and local call allowance. Only then does the host construct and execute a specialist. A subsequent step can continue the same worker or create a different specialist when the evidence calls for different expertise. Continuation starts another bounded ReAct episode with the same configuration and retained observations; it does not resume a provider session. There is no fixed roster of named worker roles. Each planning step receives the remaining model and tool call allowances, so it can stop or work from retained evidence when tools are exhausted.

`Supervisor` accepts caller-supplied DSPy LMs and tool callbacks. Model aliases and tool names must be approved by the caller; workers cannot construct providers or add tools. The two output shapes are reviewed templates. Instructions and purpose are generated data, not executable Python. An availability callback can decline a model; the supervisor then replans with the evidence intact. The availability callback reports host-known capacity; it does not demonstrate recovery from a live provider quota failure. This synchronous example has no concurrent scheduler or external-agent admission service.

A specialist needs at least two model calls: one ReAct decision and one result extraction. The planner can allocate a longer episode within the remaining mission allowance, leaving one call for supervisor assessment. A smaller allowance or one that consumes the assessment capacity is rejected before worker creation. The host counts model invocations and tool calls before execution, disables model retries on its local copies and stops when the shared or specialist allowance is exhausted. These are call limits, not monetary, token, wall-clock or provider-side retry guarantees. Callers must enforce those limits in the execution host before using paid or untrusted tools. Registered callbacks are trusted code and are not sandboxed by this example. In particular, inject a narrowly scoped read-only API function rather than an unrestricted sales assistant or a credential-bearing arbitrary executor.

The proposed configuration is checked for structure, approved capabilities and remaining calls. It is not evaluated on held-out quality cases before activation. That evaluation and a rejected-candidate fallback remain service work. The checkpoint records worker findings and host-observed execution: explicit finish, iteration limit or interruption, actual calls, and tool arguments and observations. It excludes internal thought fields. A summary extracted after an iteration limit is not evidence that the worker chose to finish. Structured observations use DSPy’s JSON serializer and are copied into the checkpoint. These records remain evidence, not verified truth. The planner also receives the active worker configuration and retains its decision reasons. The supervisor assesses whether an accessible check could change the requested decision. It may stop without an opportunity when evidence is insufficient; there is no mandatory second worker or minimum research count. A hard allowance failure before extraction can still omit the current episode from the returned checkpoint, so callers needing interruption recovery must retain tool receipts separately. A live service still needs factual validation, a comparison with ordinary DSPy on the same inputs and total resources, and an actual founder judging whether the opportunity is worth pursuing. Neither a signed identity nor another model's approval supplies that evidence.

Checks:

```bash
PYTHONPATH=. python -m pytest tests/ynot/test_runtime_specialists.py -q
```
