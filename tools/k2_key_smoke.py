from __future__ import annotations

import argparse
import json
from urllib.request import Request, urlopen

EXPECTED_MODELS = {"gpt-6.1-sol", "codex-*"}


def request_json(url: str, *, bearer: str, payload: dict[str, object] | None = None) -> dict[str, object]:
    data = None if payload is None else json.dumps(payload).encode()
    headers = {"Authorization": f"Bearer {bearer}"}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    req = Request(url, data=data, headers=headers, method="POST" if payload is not None else "GET")
    with urlopen(req, timeout=30) as response:
        return json.loads(response.read())


def generate_key(base_url: str, master_key: str) -> str:
    data = request_json(
        f"{base_url.rstrip('/')}/key/generate",
        bearer=master_key,
        payload={
            "key_alias": "codex-k2-ci",
            "duration": "15m",
            "models": sorted(EXPECTED_MODELS),
        },
    )
    key = data.get("key")
    if not isinstance(key, str) or not key.startswith("sk-"):
        raise ValueError("LiteLLM did not return a virtual key")
    return key


def verify_key_models(base_url: str, virtual_key: str) -> None:
    data = request_json(
        f"{base_url.rstrip('/')}/key/info",
        bearer=virtual_key,
    )
    info = data.get("info")
    if not isinstance(info, dict):
        raise ValueError("/key/info response did not contain an info object")
    models = info.get("models")
    if not isinstance(models, list):
        raise ValueError("/key/info response did not contain a models list")
    actual = {str(model) for model in models}
    if actual != EXPECTED_MODELS:
        raise ValueError(f"unexpected model allowlist: {sorted(actual)!r}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:4000")
    parser.add_argument("--master-key", required=True)
    args = parser.parse_args()

    virtual_key = generate_key(args.base_url, args.master_key)
    verify_key_models(args.base_url, virtual_key)
    print(json.dumps({"key_alias": "codex-k2-ci", "models": sorted(EXPECTED_MODELS)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
