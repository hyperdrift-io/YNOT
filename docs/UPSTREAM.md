# Upstream and attribution

YNOT is an independent Orchestra offering maintained by Hyperdrift. It began as a DSPy fork and preserves the engine and Git history. The original [MIT licence](../LICENSE), including `Copyright (c) 2023 Stanford Future Data Systems`, remains unchanged. DSPy and its contributors supply the programmable modules, agents and optimisation machinery on which this work builds.

- [DSPy source](https://github.com/stanfordnlp/dspy) and [upstream documentation](https://dspy.ai/).
- [DSPy research paper](https://arxiv.org/abs/2310.03714), for work that uses or discusses the underlying framework.
- Bundled lm15: [licence](../dspy/_vendor/lm15-LICENSE), [provenance](../dspy/_vendor/lm15-provenance.txt), and [update procedure](../dspy/_vendor/UPDATING.md).
- Bundled model metadata: [licence](../dspy/clients/model_metadata/LICENSE) and [provenance](../dspy/clients/model_metadata/provenance.json).

## Package boundary

`ynot-ai` is the distribution name and `ynot` is the supervised-work API. The retained engine continues to import as `dspy`. Its internal version describes the inherited engine, while the YNOT distribution has its own version. Use a separate environment from upstream DSPy because both distributions would own the same import namespace.

The retained LM integration uses bundled native lm15 engines. Keeping engine code, tests and legal notices does not make this repository an upstream DSPy release. For YNOT installation, behaviour and support, start with the [README](../README.md) and [contribution guide](../CONTRIBUTING.md).

## Repository maintenance

The inherited DSPy marketing site, site deployment and PyPI/TestPyPI publishing automation have been retired here. Their source history remains in Git. YNOT CI runs focused offline checks and verifies a built wheel; it does not publish packages or deploy a site. The wider engine tests remain available through the manual dependency-range workflow and the test directories.

Review dependencies before removing retained engine code. Preserve source provenance and licence files when updating bundled components. A change that applies upstream needs its own reproduction and must follow that project's current contribution policy.

## Model metadata

When updating the bundled fallback catalogue, select a released LiteLLM version and run `python scripts/update_model_metadata.py VERSION`. The script downloads metadata and licence files without importing LiteLLM or making model calls. Review the capability and price changes, source hashes, `snapshot.json.gz`, `provenance.json` and `LICENSE` together, then run:

```bash
LITELLM_LOCAL_MODEL_COST_MAP=True python -m pytest tests/clients/test_native_metadata.py
```

Commit reviewed metadata with the change. Building a wheel must use that snapshot rather than silently regenerating it.
