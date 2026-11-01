import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_rollout_evidence_collector_extracts_model_effort_and_parent(tmp_path):
    root = tmp_path / "sessions"
    root.mkdir()
    parent = root / "parent.jsonl"
    parent.write_text(
        "\n".join([
            json.dumps({"type":"session_meta","payload":{"id":"parent","parent_thread_id":None,"agent_role":"controller","source":"app"}}),
            json.dumps({"type":"turn_context","payload":{"model":"gpt-6.1-sol","effort":"medium"}}),
        ]) + "\n",
        encoding="utf-8",
    )
    child = root / "child.jsonl"
    child.write_text(
        "\n".join([
            json.dumps({"type":"session_meta","payload":{"id":"child","parent_thread_id":"parent","agent_role":"worker","source":"subagent"}}),
            json.dumps({"type":"turn_context","payload":{"model":"gpt-6-luna","effort":"medium"}}),
        ]) + "\n",
        encoding="utf-8",
    )

    out = tmp_path / "evidence.json"
    subprocess.run(
        [sys.executable, str(ROOT / "tools/collect_rollout_evidence.py"), "--sessions-root", str(root), "--out", str(out)],
        check=True,
    )
    data = json.loads(out.read_text(encoding="utf-8"))
    assert {x["session_id"] for x in data["sessions"]} == {"parent", "child"}
    child_row = next(x for x in data["sessions"] if x["session_id"] == "child")
    assert child_row["parent_thread_id"] == "parent"
    assert child_row["agent_role"] == "worker"
    assert child_row["model"] == "gpt-6-luna"
    assert child_row["effort"] == "medium"


def test_calibration_prompts_cover_four_router_classes():
    data = json.loads((ROOT / "configs/calibration/prompts.json").read_text(encoding="utf-8"))
    assert [x["class"] for x in data] == ["SIMPLE", "MEDIUM", "COMPLEX", "REASONING"]
    assert all(x["prompt"].strip() for x in data)
    assert all(x["expected_tier"] == x["class"] for x in data)


def test_escalation_fixture_fails_for_one_deterministic_reason():
    fixture = ROOT / "fixtures/escalation_lab"
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", str(fixture / "failure_case.py")],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert proc.returncode != 0
    combined = proc.stdout + proc.stderr
    assert "test_discount_rounding_boundary" in combined
    assert "1 failed" in combined


def test_live_validation_runbook_names_required_evidence_artifacts():
    text = (ROOT / "docs/LIVE-VALIDATION.md").read_text(encoding="utf-8")
    for name in (
        "heavy-smoke",
        "k2-passthrough.json",
        "supported-model-effort.json",
        "routing-calibration.json",
        "subagent-evidence.json",
        "escalation-evidence.json",
    ):
        assert name in text


def test_windows_evidence_wrapper_is_secret_safe():
    path = ROOT / "scripts/windows/collect-live-evidence.ps1"
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert "collect_rollout_evidence.py" in text
    assert "supported-model-effort.json" in text
    assert "Authorization" not in text
    assert "LITELLM_API_KEY=" not in text


def test_rollout_collector_tolerates_bom_unknown_and_malformed_lines(tmp_path):
    root = tmp_path / "sessions"
    root.mkdir()
    path = root / "rollout.jsonl"
    payload = (
        "\ufeff" + json.dumps({"type":"session_meta","payload":{"id":"bom-session","parent_thread_id":None,"agent_role":"controller"}})
        + "\nnot-json\n"
        + json.dumps({"type":"future_event","payload":{"ignored":True}})
        + "\n"
        + json.dumps({"type":"turn_context","payload":{"model":"gpt-6-sol","effort":{"level":"high"}}})
        + "\n"
    )
    path.write_text(payload, encoding="utf-8")

    out = tmp_path / "evidence.json"
    subprocess.run(
        [sys.executable, str(ROOT / "tools/collect_rollout_evidence.py"), "--sessions-root", str(root), "--out", str(out)],
        check=True,
    )
    data = json.loads(out.read_text(encoding="utf-8"))
    assert len(data["sessions"]) == 1
    row = data["sessions"][0]
    assert row["session_id"] == "bom-session"
    assert row["model"] == "gpt-6-sol"
    assert row["effort"] == "high"
