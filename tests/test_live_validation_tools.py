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
            json.dumps({"timestamp":"2026-11-01T00:00:00Z","ordinal":0,"type":"session_meta","payload":{"meta":{"id":"parent","parent_thread_id":None,"agent_role":"controller","source":"app"},"git":None}}),
            json.dumps({"timestamp":"2026-11-01T00:00:01Z","ordinal":1,"type":"turn_context","payload":{"model":"gpt-6.1-sol","effort":"medium"}}),
        ]) + "\n",
        encoding="utf-8",
    )
    child = root / "child.jsonl"
    child.write_text(
        "\n".join([
            json.dumps({"timestamp":"2026-11-01T00:00:02Z","ordinal":0,"type":"session_meta","payload":{"meta":{"id":"child","parent_thread_id":"parent","agent_role":"worker","source":"subagent"},"git":None}}),
            json.dumps({"timestamp":"2026-11-01T00:00:03Z","ordinal":1,"type":"turn_context","payload":{"model":"gpt-6-luna","effort":"medium"}}),
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
        "\ufeff" + json.dumps({"timestamp":"2026-11-01T00:00:00Z","ordinal":0,"type":"session_meta","payload":{"meta":{"id":"bom-session","parent_thread_id":None,"agent_role":"controller"},"git":None}})
        + "\nnot-json\n"
        + json.dumps({"type":"future_event","payload":{"ignored":True}})
        + "\n"
        + json.dumps({"timestamp":"2026-11-01T00:00:01Z","ordinal":2,"type":"turn_context","payload":{"model":"gpt-6-sol","effort":{"level":"high"}}})
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


def test_rollout_collector_fails_when_no_model_evidence_exists(tmp_path):
    root = tmp_path / "sessions"
    root.mkdir()
    (root / "empty.jsonl").write_text(
        json.dumps({"timestamp":"2026-11-01T00:00:00Z","ordinal":0,"type":"session_meta","payload":{"meta":{"id":"empty"},"git":None}}) + "\n",
        encoding="utf-8",
    )
    out = tmp_path / "evidence.json"
    proc = subprocess.run(
        [sys.executable, str(ROOT / "tools/collect_rollout_evidence.py"), "--sessions-root", str(root), "--out", str(out)],
        text=True,
        capture_output=True,
    )
    assert proc.returncode != 0
    assert "No rollout model/effort evidence found" in (proc.stdout + proc.stderr)


def test_rollout_collector_preserves_multiple_turn_contexts(tmp_path):
    root = tmp_path / "sessions"
    root.mkdir()
    path = root / "multi.jsonl"
    lines = [
        {"timestamp":"2026-11-01T00:00:00Z","ordinal":0,"type":"session_meta","payload":{"meta":{"id":"multi","agent_role":"worker"},"git":None}},
        {"timestamp":"2026-11-01T00:00:01Z","ordinal":1,"type":"turn_context","payload":{"turn_id":"t1","model":"gpt-6-luna","effort":"medium"}},
        {"timestamp":"2026-11-01T00:00:02Z","ordinal":2,"type":"turn_context","payload":{"turn_id":"t2","model":"gpt-6-sol","effort":"high"}},
    ]
    path.write_text("\n".join(json.dumps(x) for x in lines) + "\n", encoding="utf-8")
    out = tmp_path / "evidence.json"
    subprocess.run(
        [sys.executable, str(ROOT / "tools/collect_rollout_evidence.py"), "--sessions-root", str(root), "--out", str(out)],
        check=True,
    )
    data = json.loads(out.read_text(encoding="utf-8"))
    row = data["sessions"][0]
    assert row["model"] == "gpt-6-sol"
    assert row["effort"] == "high"
    assert row["turns"] == [
        {"ordinal": 1, "turn_id": "t1", "root_turn_id": None, "model": "gpt-6-luna", "effort": "medium"},
        {"ordinal": 2, "turn_id": "t2", "root_turn_id": None, "model": "gpt-6-sol", "effort": "high"},
    ]
