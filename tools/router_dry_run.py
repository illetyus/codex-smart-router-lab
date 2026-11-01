from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.request import Request, urlopen

import yaml

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_ROUTED_MODELS = {
    "luna-upstream",
    "terra-upstream",
    "sol-upstream",
    "astra-upstream",
}


def build_payload(prompt: str, config_path: Path | None = None) -> dict[str, object]:
    path = config_path or ROOT / "configs/litellm/autorouter.yaml"
    cfg = yaml.safe_load(path.read_text())
    router = next(
        m for m in cfg["model_list"]
        if m["model_name"] == "gpt-6.1-sol"
        and m["litellm_params"].get("model") == "auto_router/complexity_router"
    )
    params = router["litellm_params"]
    return {
        "prompt": prompt,
        "router_name": router["model_name"],
        "default_model": params["complexity_router_default_model"],
        "complexity_router_config": params["complexity_router_config"],
    }


def validate_response(data: dict[str, object]) -> None:
    routed = data.get("routed_model")
    if routed not in ALLOWED_ROUTED_MODELS:
        raise ValueError(f"unexpected routed_model: {routed!r}")
    decision = data.get("routing_decision")
    if not isinstance(decision, dict):
        raise ValueError("routing_decision is missing or not an object")
    if not decision:
        raise ValueError("routing_decision is empty")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:4000")
    parser.add_argument("--master-key", required=True)
    parser.add_argument(
        "--prompt",
        default="Explain why a distributed transaction can deadlock and propose a safe recovery plan.",
    )
    args = parser.parse_args()

    payload = json.dumps(build_payload(args.prompt)).encode()
    req = Request(
        f"{args.base_url.rstrip('/')}/auto_router/test_routing",
        data=payload,
        headers={
            "Authorization": f"Bearer {args.master_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urlopen(req, timeout=30) as response:
        data = json.loads(response.read())
    validate_response(data)
    print(json.dumps(data, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
