"""Qualify and reuse executable capabilities under a host-owned contract.

The executor is an injected trust boundary, not a sandbox provided by this module.
Its policy identity must be assigned by the host and changed when its authority or
behaviour changes. The store is for trusted local, single-writer use: hashes detect
inconsistent artefacts; they do not authenticate a malicious store owner. Atomic
file replacement prevents readers seeing a partly written JSON document, but does
not provide concurrent promotion/revocation transactions or crash durability.

Acceptance inputs and expected outputs are retained in memory as immutable JSON
snapshots. Saved artefacts contain their digests, not their values. Candidate source
is saved, so callers must separately prevent it from embedding private input data.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import tempfile
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from jsonschema import Draft202012Validator
from pydantic import BaseModel, ConfigDict, Field
from referencing import Registry

Executor = Callable[[str, Any], Any]


class CapabilityError(ValueError):
    """The host contract or saved capability cannot be used as supplied."""


class ExecutionLimitError(RuntimeError):
    """No execution remains in the host's allowance."""


def _canonical(value: Any) -> str:
    """Snapshot strict JSON; preserve numeric types for exact acceptance checks."""

    def check(item: Any) -> None:
        if item is None or type(item) in (str, bool, int):
            return
        if type(item) is float and math.isfinite(item):
            return
        if type(item) is list:
            for child in item:
                check(child)
            return
        if type(item) is dict and all(type(key) is str for key in item):
            for child in item.values():
                check(child)
            return
        raise CapabilityError("Value must contain only finite JSON values and string object keys")

    try:
        check(value)
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    except (RecursionError, TypeError, ValueError) as exc:
        raise CapabilityError("Value is not finite, acyclic JSON") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _source_digest(source: str) -> str:
    if not isinstance(source, str) or not source.strip():
        raise CapabilityError("Candidate source must be a non-empty string")
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def _nonempty(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CapabilityError(f"{field_name} must be a non-empty host-assigned string")
    return value


def _validator(schema: Any) -> Draft202012Validator:
    """Use a fixed schema dialect and prohibit references needing remote I/O."""

    def check_refs(value: Any) -> None:
        if isinstance(value, dict):
            if "$id" in value or "$dynamicRef" in value:
                raise CapabilityError("Schemas cannot change reference bases or use dynamic references")
            if "$ref" in value and not (
                value["$ref"] == "#" or (isinstance(value["$ref"], str) and value["$ref"].startswith("#/"))
            ):
                raise CapabilityError("Schemas may reference only local JSON pointers")
            if "$schema" in value and value["$schema"] != "https://json-schema.org/draft/2020-12/schema":
                raise CapabilityError("Only JSON Schema draft 2020-12 is supported")
            # Inspect schema positions, not instance data in const/enum/examples
            # or property names such as a literal "$ref" field.
            for keyword in ("$defs", "properties", "patternProperties", "dependentSchemas"):
                children = value.get(keyword, {})
                if isinstance(children, dict):
                    for child in children.values():
                        check_refs(child)
            for keyword in (
                "items",
                "contains",
                "additionalProperties",
                "unevaluatedProperties",
                "propertyNames",
                "not",
                "if",
                "then",
                "else",
                "unevaluatedItems",
                "contentSchema",
            ):
                if keyword in value:
                    check_refs(value[keyword])
            for keyword in ("allOf", "anyOf", "oneOf", "prefixItems"):
                children = value.get(keyword, [])
                if isinstance(children, list):
                    for child in children:
                        check_refs(child)

    check_refs(schema)
    Draft202012Validator.check_schema(schema)
    # A local pointer can reach a schema under an otherwise unknown keyword.
    # Disable retrieval independently of the syntactic checks above.
    return Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER, registry=Registry())


@dataclass(frozen=True, init=False)
class AcceptanceCase:
    """A host-authored input and its exact expected JSON result."""

    _payload_json: str = field(repr=False)
    _expected_json: str = field(repr=False)

    def __init__(self, payload: Any, expected: Any):
        object.__setattr__(self, "_payload_json", _canonical(payload))
        object.__setattr__(self, "_expected_json", _canonical(expected))

    @property
    def payload(self) -> Any:
        return json.loads(self._payload_json)

    @property
    def expected(self) -> Any:
        return json.loads(self._expected_json)


@dataclass(frozen=True, init=False)
class CapabilityContract:
    """Immutable host-owned schemas, version and acceptance cases.

    This contract is supplied by trusted application code, never accepted from a
    candidate's response. Passing the cases supports only their recorded scope.
    """

    name: str
    version: str
    _definition_json: str = field(repr=False)

    def __init__(
        self,
        name: str,
        version: str,
        input_schema: Any,
        output_schema: Any,
        cases: list[AcceptanceCase] | tuple[AcceptanceCase, ...],
    ):
        if not cases or not all(isinstance(case, AcceptanceCase) for case in cases):
            raise CapabilityError("A contract needs at least one host-owned acceptance case")
        definition = {
            "name": _nonempty(name, "name"),
            "version": _nonempty(version, "version"),
            "input_schema": input_schema,
            "output_schema": output_schema,
            "cases": [{"payload": case.payload, "expected": case.expected} for case in cases],
        }
        snapshot = _canonical(definition)
        owned = json.loads(snapshot)
        input_validator = _validator(owned["input_schema"])
        output_validator = _validator(owned["output_schema"])
        for case in owned["cases"]:
            input_validator.validate(case["payload"])
            output_validator.validate(case["expected"])
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "version", version)
        object.__setattr__(self, "_definition_json", snapshot)

    @property
    def input_schema(self) -> Any:
        return json.loads(self._definition_json)["input_schema"]

    @property
    def output_schema(self) -> Any:
        return json.loads(self._definition_json)["output_schema"]

    @property
    def cases(self) -> tuple[AcceptanceCase, ...]:
        return tuple(AcceptanceCase(**case) for case in json.loads(self._definition_json)["cases"])

    @property
    def digest(self) -> str:
        return hashlib.sha256(self._definition_json.encode("utf-8")).hexdigest()

    @property
    def cases_digest(self) -> str:
        return _digest(json.loads(self._definition_json)["cases"])


@dataclass
class ExecutionAllowance:
    """Count attempted executor calls, including failed qualification and reuse."""

    limit: int
    used: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if type(self.limit) is not int or type(self.used) is not int or not 0 <= self.used <= self.limit:
            raise CapabilityError("Execution allowance requires integers with 0 <= used <= limit")

    def consume(self) -> None:
        with self._lock:
            if self.used >= self.limit:
                raise ExecutionLimitError("Capability execution allowance exhausted")
            self.used += 1


class CaseReceipt(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    index: int = Field(ge=0)
    passed: bool
    reason: str


class QualificationReceipt(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    capability_id: str
    source_sha256: str
    contract_sha256: str
    cases_sha256: str
    input_schema_sha256: str
    output_schema_sha256: str
    contract_name: str
    contract_version: str
    scope: str
    executor_policy: str
    cases: tuple[CaseReceipt, ...]
    executions: int = Field(ge=0)
    qualified_at: str


class QualificationResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    receipt: QualificationReceipt
    promoted: bool
    capability_id: str | None


class _Revocation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    reason: str
    revoked_at: str


class _Artifact(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    format_version: Literal[1] = 1
    capability_id: str
    source: str
    receipt: QualificationReceipt
    revocation: _Revocation | None = None


def _identity(source_sha256: str, contract_sha256: str, scope: str, executor_policy: str) -> str:
    return _digest(
        {
            "source_sha256": source_sha256,
            "contract_sha256": contract_sha256,
            "scope": scope,
            "executor_policy": executor_policy,
        }
    )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class CapabilityStore:
    """A scoped local store. ``run`` validates and activates afresh on every call.

    There is no cached callable which can bypass a later revocation. The caller
    must supply the same host contract and executor policy on qualification and
    reuse. Contract cases are required in memory but never written into the store.
    """

    def __init__(self, path: str | Path, scope: str, executor_policy: str):
        self.scope = _nonempty(scope, "scope")
        self.executor_policy = _nonempty(executor_policy, "executor_policy")
        self.path = Path(path) / _digest(scope)
        self.path.mkdir(parents=True, exist_ok=True)

    def _path(self, capability_id: str) -> Path:
        if not isinstance(capability_id, str) or not re.fullmatch(r"[0-9a-f]{64}", capability_id):
            raise CapabilityError("Unknown capability identity")
        return self.path / f"{capability_id}.json"

    def _load(self, capability_id: str) -> _Artifact:
        try:
            artifact = _Artifact.model_validate_json(self._path(capability_id).read_bytes())
        except (OSError, ValueError) as exc:
            raise CapabilityError("Unknown or invalid saved capability") from exc
        receipt = artifact.receipt
        identity = _identity(_source_digest(artifact.source), receipt.contract_sha256, self.scope, self.executor_policy)
        if (
            artifact.capability_id != capability_id
            or receipt.capability_id != capability_id
            or identity != capability_id
            or receipt.source_sha256 != _source_digest(artifact.source)
            or receipt.scope != self.scope
            or receipt.executor_policy != self.executor_policy
            or not receipt.cases
            or not all(case.passed for case in receipt.cases)
            or [case.index for case in receipt.cases] != list(range(len(receipt.cases)))
            or receipt.executions != len(receipt.cases)
        ):
            raise CapabilityError("Saved capability identity or qualification is inconsistent")
        return artifact

    @staticmethod
    def _check_contract(artifact: _Artifact, contract: CapabilityContract) -> None:
        receipt = artifact.receipt
        if (
            receipt.contract_sha256 != contract.digest
            or receipt.cases_sha256 != contract.cases_digest
            or receipt.input_schema_sha256 != _digest(contract.input_schema)
            or receipt.output_schema_sha256 != _digest(contract.output_schema)
            or receipt.contract_name != contract.name
            or receipt.contract_version != contract.version
            or len(receipt.cases) != len(contract.cases)
        ):
            raise CapabilityError("Saved capability does not match the host contract")

    def _save(self, artifact: _Artifact) -> None:
        destination = self._path(artifact.capability_id)
        temporary_path: str | None = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.path, delete=False) as output:
                temporary_path = output.name
                output.write(artifact.model_dump_json(indent=2))
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary_path, destination)
            temporary_path = None
        finally:
            if temporary_path is not None:
                Path(temporary_path).unlink(missing_ok=True)

    def qualify(
        self,
        source: str,
        contract: CapabilityContract,
        executor: Executor,
        allowance: ExecutionAllowance,
    ) -> QualificationResult:
        """Execute every acceptance case; only an entirely passing candidate is saved.

        Execution exhaustion raises and never promotes a partial qualification.
        Other executor/check failures produce a receipt without private values or
        exception messages. The previous saved capabilities remain available.
        """
        source_sha256 = _source_digest(source)
        capability_id = _identity(source_sha256, contract.digest, self.scope, self.executor_policy)
        if self._path(capability_id).exists():
            existing = self._load(capability_id)
            self._check_contract(existing, contract)
            if existing.revocation is not None:
                raise CapabilityError("This capability was revoked; qualification cannot reactivate it")
        output_validator = _validator(contract.output_schema)
        cases: list[CaseReceipt] = []
        for index, case in enumerate(contract.cases):
            allowance.consume()
            try:
                output = executor(source, case.payload)
            except ExecutionLimitError:
                raise
            except Exception as exc:
                cases.append(CaseReceipt(index=index, passed=False, reason=f"executor_error:{type(exc).__name__}"))
                continue
            try:
                output_json = _canonical(output)
                output_validator.validate(json.loads(output_json))
            except Exception:
                cases.append(CaseReceipt(index=index, passed=False, reason="invalid_output"))
                continue
            passed = output_json == case._expected_json
            cases.append(CaseReceipt(index=index, passed=passed, reason="matched" if passed else "unexpected_output"))
        receipt = QualificationReceipt(
            capability_id=capability_id,
            source_sha256=source_sha256,
            contract_sha256=contract.digest,
            cases_sha256=contract.cases_digest,
            input_schema_sha256=_digest(contract.input_schema),
            output_schema_sha256=_digest(contract.output_schema),
            contract_name=contract.name,
            contract_version=contract.version,
            scope=self.scope,
            executor_policy=self.executor_policy,
            cases=tuple(cases),
            executions=len(cases),
            qualified_at=_now(),
        )
        promoted = all(case.passed for case in cases)
        if promoted:
            # Do not revive a capability revoked while its checks were running.
            if self._path(capability_id).exists() and self._load(capability_id).revocation is not None:
                raise CapabilityError("Capability was revoked during qualification")
            self._save(_Artifact(capability_id=capability_id, source=source, receipt=receipt))
        return QualificationResult(
            receipt=receipt, promoted=promoted, capability_id=capability_id if promoted else None
        )

    def run(
        self,
        capability_id: str,
        payload: Any,
        contract: CapabilityContract,
        executor: Executor,
        allowance: ExecutionAllowance,
    ) -> Any:
        """Activate a saved version and return a detached, schema-checked JSON value."""
        artifact = self._load(capability_id)
        self._check_contract(artifact, contract)
        if artifact.revocation is not None:
            raise CapabilityError("Capability has been revoked")
        payload_json = _canonical(payload)
        _validator(contract.input_schema).validate(json.loads(payload_json))
        allowance.consume()
        output = executor(artifact.source, json.loads(payload_json))
        snapshot = json.loads(_canonical(output))
        _validator(contract.output_schema).validate(snapshot)
        return snapshot

    def revoke(self, capability_id: str, reason: str) -> None:
        """Prevent subsequent activation; an execution already in progress is unaffected."""
        artifact = self._load(capability_id)
        if artifact.revocation is not None:
            return
        revocation = _Revocation(reason=_nonempty(reason, "revocation reason"), revoked_at=_now())
        self._save(artifact.model_copy(update={"revocation": revocation}))
