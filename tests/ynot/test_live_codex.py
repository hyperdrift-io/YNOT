import json
import subprocess

import pytest

from dspy.lm15 import ImagePart, Message, Request
from examples.ynot.live_codex import CodexEngine, CodexHost, CodexResearch, LiveRunError, _execute, _schema
from examples.ynot.service_adviser import Criterion, EvidencePacket, FounderNeed, TrialObservation


def events(answer="hello", web=()):
    return "\n".join(
        json.dumps(item)
        for item in [
            *(
                {"type": "item.completed", "item": {"type": "web_search", "action": {"type": "open_page", "url": url}}}
                for url in web
            ),
            {"type": "item.completed", "item": {"type": "agent_message", "text": answer}},
            {"type": "turn.completed", "usage": {"input_tokens": 20, "output_tokens": 5}},
        ]
    )


def fake_run(monkeypatch, output, code=0):
    calls = []

    def run(command, prompt, cwd, timeout):
        calls.append((command, prompt, timeout))
        return subprocess.CompletedProcess(command, code, output, "private diagnostics")

    monkeypatch.setattr("examples.ynot.live_codex._execute", run)
    return calls


def test_text_engine_uses_existing_auth_and_counts_all_invocations(tmp_path, monkeypatch):
    calls = fake_run(monkeypatch, events())
    host = CodexHost(tmp_path, max_invocations=1)
    engine = CodexEngine(host)
    response = engine.complete(Request(model="custom/test", messages=(Message.user("question"),)))
    assert response.message.parts[0].text == "hello"
    assert response.usage.input_tokens == 20
    command = calls[0][0]
    assert "--ignore-user-config" in command and "--ephemeral" in command
    assert 'web_search="disabled"' in command and "features.shell_tool=false" in command
    assert "--model" not in command
    assert host.calls[0]["status"] == "completed"
    assert "private diagnostics" not in "".join(path.read_text() for path in tmp_path.glob("*.json*"))
    with pytest.raises(LiveRunError, match="allowance"):
        engine.complete(Request(model="custom/test", messages=(Message.user("again"),)))
    assert len(calls) == 1


@pytest.mark.parametrize("output,code,error", [("bad", 0, "malformed"), ("", 1, "exited"), ("", 0, "complete")])
def test_cli_failure_is_recorded(tmp_path, monkeypatch, output, code, error):
    fake_run(monkeypatch, output, code)
    host = CodexHost(tmp_path)
    with pytest.raises(LiveRunError, match=error):
        host.invoke("public prompt")
    assert json.loads((tmp_path / "host-usage.json").read_text())[0]["status"] == "failed"


def test_plain_inference_rejects_unexpected_web_tools(tmp_path, monkeypatch):
    fake_run(monkeypatch, events(web=["https://exa.ai/docs"]))
    with pytest.raises(LiveRunError, match="capabilities"):
        CodexHost(tmp_path).invoke("prompt")


def test_multimodal_input_never_reaches_cli(tmp_path, monkeypatch):
    calls = fake_run(monkeypatch, events())
    request = Request(model="custom/test", messages=(Message.user(ImagePart(url="https://example.org/a.png")),))
    with pytest.raises(ValueError, match="text parts only"):
        CodexEngine(CodexHost(tmp_path)).complete(request)
    assert not calls


def packet(url="https://exa.ai/docs"):
    return {
        "sources": [
            {
                "id": "source1",
                "service": "Exa",
                "url": url,
                "excerpt": "Documented research API.",
                "checked_at": "2026-10-30",
            }
        ],
        "assessments": [
            {
                "service": "Exa",
                "findings": [
                    {"criterion_id": "research", "status": "meets", "source_id": "source1", "detail": "API documented."}
                ],
            }
        ],
    }


@pytest.mark.parametrize(
    "observed,url,accepted",
    [
        ([], "https://exa.ai/docs", False),
        (["https://exa.ai/docs"], "https://evil.example/claim", False),
        (["https://exa.ai/docs"], "https://exa.ai/docs", True),
    ],
)
def test_research_requires_primary_domain_and_observed_url(tmp_path, monkeypatch, observed, url, accepted):
    fake_run(monkeypatch, events(json.dumps(packet(url)), web=observed))
    host = CodexHost(tmp_path)
    need = FounderNeed(outcome="Research", criteria=[Criterion(id="research", description="Research API")])
    research = CodexResearch(host, need, ["exa.ai"])
    if accepted:
        assert research("Exa", "API?").sources[0].id == "source1"
        assert host.calls[0]["kind"] == "research"
        assert host.calls[0]["web_actions"] == 1
    else:
        with pytest.raises(ValueError):
            research("Exa", "API?")
        assert not research.packets


def test_schema_is_strict():
    schema = _schema()
    assert schema["required"] == ["sources", "assessments"]
    for record in schema["$defs"].values():
        assert record["additionalProperties"] is False
        assert record["required"] == list(record["properties"])
    assert EvidencePacket.model_validate(packet())


def test_research_receives_a_saved_snapshot_of_founder_and_trial_context(tmp_path, monkeypatch):
    calls = fake_run(monkeypatch, events(json.dumps(packet()), web=["https://exa.ai/docs"]))
    need = FounderNeed(
        outcome="Research",
        criteria=[Criterion(id="research", description="Research API")],
        founder_brief="The founder already supplied the offer and target customer.",
        trial_observations=[
            TrialObservation(summary="One public trial completed.", observed_at="2026-10-30", evidence_ref="trial-01")
        ],
    )
    saved = need.model_dump_json()
    need = FounderNeed.model_validate_json(saved)
    research = CodexResearch(CodexHost(tmp_path), need, ["exa.ai"])
    need.founder_brief = "Later caller edit"
    need.trial_observations[0].summary = "Later observation edit"
    research("Exa", "Assess the retained brief")
    assert '"founder_brief": "The founder already supplied the offer and target customer."' in calls[0][1]
    assert '"observed_at": "2026-10-30"' in calls[0][1]
    assert '"evidence_ref": "trial-01"' in calls[0][1]
    assert '"summary": "One public trial completed."' in calls[0][1]


def test_timeout_kills_process_group(monkeypatch):
    class Process:
        pid = 123
        calls = 0

        def communicate(self, *args, **kwargs):
            self.calls += 1
            if self.calls == 1:
                raise subprocess.TimeoutExpired("codex", 1)
            return "", ""

    killed = []
    monkeypatch.setattr("examples.ynot.live_codex.subprocess.Popen", lambda *args, **kwargs: Process())
    monkeypatch.setattr("examples.ynot.live_codex.os.killpg", lambda pid, sig: killed.append(pid))
    with pytest.raises(LiveRunError, match="timed out"):
        _execute(["codex"], "prompt", "/tmp", 1)
    assert killed == [123]


def test_search_query_url_cannot_satisfy_source_gate(tmp_path, monkeypatch):
    output = events(json.dumps(packet()))
    search = {
        "type": "item.completed",
        "item": {
            "type": "web_search",
            "action": {"type": "search", "query": "https://exa.ai/docs", "url": "https://exa.ai/docs"},
        },
    }
    fake_run(monkeypatch, json.dumps(search) + "\n" + output)
    host = CodexHost(tmp_path)
    need = FounderNeed(outcome="Research", criteria=[Criterion(id="research", description="Research API")])
    with pytest.raises(ValueError, match="attempted-open"):
        CodexResearch(host, need, ["exa.ai"])("Exa", "API?")
    assert host.calls[0]["observed_urls"] == []
    assert host.calls[0]["url_evidence"] == "attempted_open_only"


def test_timeout_retains_partial_public_events(tmp_path, monkeypatch):
    partial = json.dumps({"type": "turn.started"}) + "\n"

    def timeout(*args):
        raise LiveRunError("Codex CLI invocation timed out.", stdout=partial)

    monkeypatch.setattr("examples.ynot.live_codex._execute", timeout)
    host = CodexHost(tmp_path)
    with pytest.raises(LiveRunError, match="timed out"):
        host.invoke("Public research brief")
    assert (tmp_path / "01-events.jsonl").read_text() == partial
    assert (tmp_path / "01-request.txt").read_text() == "Public research brief"
    assert host.calls[0]["partial_trace"] is True


def test_batch_open_accepts_page_result_urls_and_counts_action_once(tmp_path, monkeypatch):
    action = {
        "id": "web1",
        "type": "web_search",
        "action": {"type": "open_page", "url": "https://exa.ai/docs/start"},
        "results": [
            {
                "type": "text_result",
                "url": "https://exa.ai/docs",
                "thumbnail_url": "https://image.example/a.png",
                "snippet": "Total lines: 100",
            }
        ],
    }
    placeholder = {"id": "web1", "type": "web_search", "action": {"type": "other"}}
    output = "\n".join(json.dumps({"type": "item.completed", "item": item}) for item in [placeholder, action])
    fake_run(monkeypatch, output + "\n" + events(json.dumps(packet())))
    host = CodexHost(tmp_path)
    need = FounderNeed(outcome="Research", criteria=[Criterion(id="research", description="Research API")])
    result = CodexResearch(host, need, ["exa.ai"])("Exa", "API?")
    assert result.sources[0].id == "source1"
    assert host.calls[0]["web_actions"] == 1
    assert host.calls[0]["web_event_items"] == 2
    assert host.calls[0]["observed_urls"] == ["https://exa.ai/docs", "https://exa.ai/docs/start"]


@pytest.mark.parametrize("mismatched", ["source", "assessment"])
def test_research_rejects_service_aliases(tmp_path, monkeypatch, mismatched):
    evidence = packet()
    if mismatched == "source":
        evidence["sources"][0]["service"] = "Exa Search"
    else:
        evidence["assessments"][0]["service"] = "Exa Search"
    calls = fake_run(monkeypatch, events(json.dumps(evidence), web=["https://exa.ai/docs"]))
    host = CodexHost(tmp_path)
    need = FounderNeed(outcome="Research", criteria=[Criterion(id="research", description="Research API")])
    research = CodexResearch(host, need, ["exa.ai"])
    with pytest.raises(ValueError, match="exactly match"):
        research("Exa", "API?")
    assert not research.packets
    assert '"snapshot_prefix": "cli-01-"' in calls[0][1]
