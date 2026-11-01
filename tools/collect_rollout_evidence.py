#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


def _meta(payload):
    if isinstance(payload, dict) and isinstance(payload.get("meta"), dict):
        merged = dict(payload)
        merged.update(payload["meta"])
        return merged
    return payload if isinstance(payload, dict) else {}


def _effort(value):
    if isinstance(value, str) or value is None:
        return value
    if isinstance(value, dict):
        for key in ("level", "effort", "value"):
            if isinstance(value.get(key), str):
                return value[key]
    return value


def inspect_rollout(path: Path):
    meta = {}
    turn = {}
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            item = json.loads(raw)
        except json.JSONDecodeError:
            continue
        kind = item.get("type")
        payload = item.get("payload") or {}
        if kind == "session_meta" and not meta:
            meta = _meta(payload)
        elif kind == "turn_context":
            turn = payload

    if not meta and not turn:
        return None

    session_id = (
        meta.get("id")
        or meta.get("thread_id")
        or meta.get("session_id")
        or path.stem
    )
    source = meta.get("source")
    if not isinstance(source, (str, int, float, bool, type(None))):
        source = source

    return {
        "file": str(path),
        "session_id": str(session_id),
        "parent_thread_id": meta.get("parent_thread_id"),
        "agent_role": meta.get("agent_role"),
        "source": source,
        "model": turn.get("model"),
        "effort": _effort(turn.get("effort")),
        "turn_id": turn.get("turn_id"),
        "root_turn_id": turn.get("root_turn_id"),
    }


def collect(root: Path):
    sessions = []
    for path in sorted(root.rglob("*.jsonl")):
        row = inspect_rollout(path)
        if row:
            sessions.append(row)
    return {
        "schema_version": 1,
        "sessions_root": str(root),
        "sessions": sessions,
    }


def main():
    parser = argparse.ArgumentParser(description="Collect Codex rollout model/effort evidence.")
    parser.add_argument("--sessions-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    result = collect(args.sessions_root)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(result['sessions'])} session records to {args.out}")


if __name__ == "__main__":
    main()
