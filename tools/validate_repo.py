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


    expected_postgres = "postgres:16.15-bookworm@sha256:e8a07d2c7579b038938cdba6c539e580e5001caf9ea203d397b5cc83e76bd938"
    if compose["services"]["db"].get("image") != expected_postgres:
        errors.append("CI Postgres image must remain pinned to the reviewed PostgreSQL 16.15 digest")

    install_text = (ROOT / "scripts/windows/install.ps1").read_text()
    preflight_text = (ROOT / "scripts/windows/preflight.ps1").read_text()
    launcher_text = (ROOT / "scripts/windows/start-router.ps1").read_text()
    if "[string]$Runtime = 'native'" not in install_text:
        errors.append("Native Windows must remain the default user runtime")
    if PINNED_LITELLM_REF not in install_text or "--frozen" not in install_text or "--python 3.13" not in install_text:
        errors.append("Native installer must reproduce the audited pinned LiteLLM source environment")
    if "[string]$Runtime = 'native'" not in preflight_text:
        errors.append("Native Windows preflight must remain the default")
    for required in ("uv", "node", "psql", "pg_isready"):
        if f"Test-Command '{required}'" not in preflight_text:
            errors.append(f"Native preflight must check {required}")
    if "--host 127.0.0.1" not in launcher_text:
        errors.append("Native LiteLLM launcher must bind explicitly to IPv4 loopback")
    for name in ("STORE_MODEL_IN_DB", "DISABLE_ADMIN_UI", "NO_DOCS", "NO_REDOC", "NO_OPENAPI", "CHECKPOINT_DISABLE"):
        if name not in launcher_text:
            errors.append(f"Native launcher must restore hardening variable {name}")
    if "OPENAI_API_KEY is prohibited" not in launcher_text:
        errors.append("Native launcher must fail closed if OPENAI_API_KEY is injected")

    expected_hardening_env = {
        "DISABLE_ADMIN_UI": "True",
        "NO_DOCS": "True",
        "NO_REDOC": "True",
        "NO_OPENAPI": "True",
    }
    for key, value in expected_hardening_env.items():
        if litellm.get("environment", {}).get(key) != value:
            errors.append(f"LiteLLM hardening env {key} must remain {value}")

    for config_name in ("subscription.yaml", "model-probe.yaml", "autorouter.yaml"):
        cfg = yaml.safe_load((ROOT / "configs/litellm" / config_name).read_text())
        if cfg.get("general_settings", {}).get("trusted_proxy_ranges") != []:
            errors.append(f"{config_name} must set trusted_proxy_ranges to [] for direct localhost clients")
        duration_cap = (
            cfg.get("litellm_settings", {})
            .get("upperbound_key_generate_params", {})
            .get("duration")
        )
        if duration_cap != "30d":
            errors.append(f"{config_name} must enforce a 30d virtual-key duration upper bound")

    sub = yaml.safe_load((ROOT / "configs/litellm/subscription.yaml").read_text())
    sub_text = json.dumps(sub)
    if "openai/" in sub_text or "OPENAI_API_KEY" in sub_text:
        errors.append("Paid OpenAI API fallback must remain disabled")
    if "CHATGPT_TOKEN_DIR" in sub_text or "auth.json" in sub_text:
        errors.append("Baseline must use Codex-forwarded ChatGPT auth, not a saved proxy login")
    sub_routes = {m["model_name"]: m["litellm_params"].get("model") for m in sub["model_list"]}
    if sub_routes.get("codex-*") != "chatgpt/codex-*":
        errors.append("Baseline must preserve codex-* approval/review passthrough")
    if sub_routes.get("gpt-image-2") != "chatgpt/gpt-image-2":
        errors.append("Baseline must preserve Codex gpt-image-2 subscription routing")

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
    if auto_routes.get("gpt-image-2") != "chatgpt/gpt-image-2":
        errors.append("Auto Router config must preserve Codex gpt-image-2 subscription routing")

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
    if provider.get("base_url") != "http://127.0.0.1:4000/v1":
        errors.append("Codex provider must use the same IPv4 loopback address the gateway binds")
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
