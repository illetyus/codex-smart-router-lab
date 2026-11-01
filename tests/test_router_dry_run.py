from pathlib import Path
import importlib.util
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("router_dry_run", ROOT / "tools/router_dry_run.py")
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
ALLOWED_ROUTED_MODELS = module.ALLOWED_ROUTED_MODELS
build_payload = module.build_payload
validate_response = module.validate_response


def test_build_payload_uses_exact_committed_router_contract():
    payload = build_payload("hello", ROOT / "configs/litellm/autorouter.yaml")
    assert payload["router_name"] == "gpt-6.1-sol"
    assert payload["default_model"] == "terra-upstream"
    cfg = payload["complexity_router_config"]
    assert cfg["classifier_type"] == "heuristic"
    assert cfg["classification_mode"] == "user_turn"
    assert cfg["context_compaction"] is False
    assert cfg["tiers"] == {
        "SIMPLE": "luna-upstream",
        "MEDIUM": "terra-upstream",
        "COMPLEX": "sol-upstream",
        "REASONING": "astra-upstream",
    }


def test_validate_response_accepts_realistic_router_decision_shape():
    validate_response({
        "routed_model": "sol-upstream",
        "routed_model_configured": True,
        "routing_decision": {"tier": "COMPLEX", "cause": "heuristic"},
    })


def test_validate_response_rejects_model_outside_the_internal_ladder():
    with pytest.raises(ValueError, match="unexpected routed_model"):
        validate_response({
            "routed_model": "openai-paid-fallback",
            "routing_decision": {"tier": "COMPLEX"},
        })


def test_allowed_models_match_internal_ladder_only():
    assert ALLOWED_ROUTED_MODELS == {
        "luna-upstream", "terra-upstream", "sol-upstream", "astra-upstream"
    }
