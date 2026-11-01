from __future__ import annotations
from pathlib import Path
import json
import sys
import tomllib
import yaml

ROOT = Path(__file__).resolve().parents[1]
PINNED_LITELLM_REF = "4bdeb1378bb19a453cd3c49d383ebe76f057d2c6"


def validate() -> list[str]:
    errors: list[str] = []
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text())
    litellm = compose["services"]["litellm"]
    if litellm.get("ports") != ["127.0.0.1:4000:4000"]:
        errors.append("LiteLLM must bind only to 127.0.0.1:4000")
    if "ports" in compose["services"]["db"]:
        errors.append("Postgres must not publish a host port")
    expected_context = f"https://github.com/BerriAI/litellm.git#{PINNED_LITELLM_REF}"
    if litellm["build"].get("context") != expected_context:
        errors.append("LiteLLM source context is not pinned to the reviewed full SHA")

    sub = yaml.safe_load((ROOT / "configs/litellm/subscription.yaml").read_text())
    sub_text = json.dumps(sub)
    if "openai/" in sub_text or "OPENAI_API_KEY" in sub_text:
        errors.append("Paid OpenAI API fallback must remain disabled")
    if "CHATGPT_TOKEN_DIR" in sub_text or "auth.json" in sub_text:
        errors.append("Baseline must use Codex-forwarded ChatGPT auth, not a saved proxy login")
    sub_routes = {m["model_name"]: m["litellm_params"].get("model") for m in sub["model_list"]}
    if sub_routes.get("codex-*") != "chatgpt/codex-*":
        errors.append("Baseline must preserve codex-* approval/review passthrough")

    auto = yaml.safe_load((ROOT / "configs/litellm/autorouter.yaml").read_text())
    routers = [
        m for m in auto["model_list"]
        if m["model_name"] == "gpt-6.1-sol"
        and m["litellm_params"].get("model") == "auto_router/complexity_router"
    ]
    if len(routers) != 1:
        errors.append("Auto Router must shadow the known gpt-6.1-sol Codex slug exactly once")
        return errors
    router = routers[0]
    rcfg = router["litellm_params"]["complexity_router_config"]
    if rcfg.get("context_compaction") is not False:
        errors.append("Auto Router context_compaction must remain false for subscription passthrough")
    if rcfg.get("stall_escalation_enabled") is not False:
        errors.append("Stall escalation is intentionally disabled in phase 1")
    expected_tiers = {
        "SIMPLE": "luna-upstream",
        "MEDIUM": "terra-upstream",
        "COMPLEX": "sol-upstream",
        "REASONING": "astra-upstream",
    }
    if rcfg.get("tiers") != expected_tiers:
        errors.append("Auto Router tiers do not match the reviewed Luna/Terra/Sol/Astra ladder")

    upstream_models = {
        m["model_name"]: m["litellm_params"].get("model")
        for m in auto["model_list"]
        if m["model_name"].endswith("-upstream")
    }
    auto_routes = {
        m["model_name"]: m["litellm_params"].get("model")
        for m in auto["model_list"]
    }
    if auto_routes.get("codex-*") != "chatgpt/codex-*":
        errors.append("Auto Router config must preserve codex-* approval/review passthrough")

    expected_upstreams = {
        "luna-upstream": "chatgpt/gpt-6-luna",
        "terra-upstream": "chatgpt/gpt-6.1-terra",
        "sol-upstream": "chatgpt/gpt-6.1-sol",
        "astra-upstream": "chatgpt/gpt-6-astra",
    }
    if upstream_models != expected_upstreams:
        errors.append("Auto Router upstream model map differs from the reviewed current Codex model set")

    expected_direct_workers = {
        "gpt-6-luna": "chatgpt/gpt-6-luna",
        "gpt-6.1-terra": "chatgpt/gpt-6.1-terra",
        "gpt-6-sol": "chatgpt/gpt-6-sol",
        "gpt-6-astra": "chatgpt/gpt-6-astra",
    }
    direct_workers = {
        name: auto_routes.get(name)
        for name in expected_direct_workers
    }
    if direct_workers != expected_direct_workers:
        errors.append("Direct Superpowers worker routes do not match the reviewed Codex model slugs")
    if any(m["model_name"] == "gpt-*" for m in auto["model_list"]):
        errors.append("Do not use a broad gpt-* wildcard for worker routing")

    codex = tomllib.loads((ROOT / "configs/codex/provider.subscription.toml").read_text())
    provider = codex["model_providers"]["litellm_subscription"]
    if provider.get("requires_openai_auth") is not True:
        errors.append("Codex provider must preserve ChatGPT authentication")
    if "env_key" in provider:
        errors.append("Codex provider must not replace ChatGPT Authorization with a gateway key")
    return errors


def main() -> int:
    errors = validate()
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("Repository contract OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
