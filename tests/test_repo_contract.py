from pathlib import Path
import json
import tomllib
import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_required_files_exist():
    required = [
        'README.md', 'LICENSE', '.gitignore', '.env.example',
        'docker-compose.yml', 'configs/litellm/subscription.yaml',
        'configs/litellm/autorouter.yaml',
        'configs/codex/provider.subscription.toml',
        'scripts/windows/preflight.ps1', 'scripts/windows/install.ps1',
        'scripts/windows/verify.ps1', 'scripts/windows/uninstall.ps1',
        '.github/workflows/ci.yml', 'tools/validate_repo.py',
    ]
    missing = [p for p in required if not (ROOT / p).exists()]
    assert not missing, f'missing: {missing}'


def test_compose_is_local_only_and_postgres_not_published():
    data = yaml.safe_load((ROOT / 'docker-compose.yml').read_text())
    litellm = data['services']['litellm']
    assert litellm['ports'] == ['127.0.0.1:4000:4000']
    assert 'ports' not in data['services']['db']
    assert data['services']['db']['image'].startswith('postgres:16')


def test_compose_uses_pinned_litellm_source_ref():
    data = yaml.safe_load((ROOT / 'docker-compose.yml').read_text())
    context = data['services']['litellm']['build']['context']
    assert context == 'https://github.com/BerriAI/litellm.git#4bdeb1378bb19a453cd3c49d383ebe76f057d2c6'


def test_subscription_baseline_is_one_explicit_chatgpt_model_with_no_paid_fallback():
    cfg = yaml.safe_load((ROOT / 'configs/litellm/subscription.yaml').read_text())
    models = cfg['model_list']
    assert models == [{
        'model_name': 'gpt-6.1-sol',
        'litellm_params': {'model': 'chatgpt/gpt-6.1-sol'},
        'model_info': {'mode': 'responses'},
    }]
    serialized = json.dumps(cfg)
    assert 'openai/' not in serialized
    assert 'OPENAI_API_KEY' not in serialized
    assert 'CHATGPT_TOKEN_DIR' not in serialized
    assert 'auth.json' not in serialized


def test_autorouter_shadows_known_codex_slug_and_uses_current_chatgpt_models():
    cfg = yaml.safe_load((ROOT / 'configs/litellm/autorouter.yaml').read_text())
    models = cfg['model_list']
    router = next(x for x in models if x['model_name'] == 'gpt-6.1-sol')
    rcfg = router['litellm_params']['complexity_router_config']
    assert rcfg['context_compaction'] is False
    assert rcfg['classification_mode'] == 'user_turn'
    assert rcfg['stall_escalation_enabled'] is False
    assert rcfg['tiers'] == {
        'SIMPLE': 'luna-upstream',
        'MEDIUM': 'terra-upstream',
        'COMPLEX': 'sol-upstream',
        'REASONING': 'astra-upstream',
    }
    assert router['litellm_params']['complexity_router_default_model'] == 'terra-upstream'
    upstreams = [x for x in models if x is not router]
    actual = {x['model_name']: x['litellm_params']['model'] for x in upstreams}
    assert actual == {
        'luna-upstream': 'chatgpt/gpt-6-luna',
        'terra-upstream': 'chatgpt/gpt-6.1-terra',
        'sol-upstream': 'chatgpt/gpt-6.1-sol',
        'astra-upstream': 'chatgpt/gpt-6-astra',
    }


def test_codex_provider_preserves_chatgpt_auth():
    cfg = tomllib.loads((ROOT / 'configs/codex/provider.subscription.toml').read_text())
    provider = cfg['model_providers']['litellm_subscription']
    assert provider['requires_openai_auth'] is True
    assert provider['supports_websockets'] is False
    assert 'env_key' not in provider
    assert provider['env_http_headers']['x-litellm-api-key'] == 'LITELLM_API_KEY'


def test_env_example_contains_no_real_secrets():
    text = (ROOT / '.env.example').read_text()
    assert 'sk-' not in text
    assert 'OPENAI_API_KEY' not in text
    assert 'CHANGE_ME' in text


def test_compose_selects_config_from_environment():
    data = yaml.safe_load((ROOT / 'docker-compose.yml').read_text())
    command = data['services']['litellm']['command']
    assert '${CODEX_ROUTER_CONFIG:-subscription.yaml}' in command[0]


def test_autorouter_uses_upstream_tier_model_configs_shape():
    cfg = yaml.safe_load((ROOT / 'configs/litellm/autorouter.yaml').read_text())
    router = next(x for x in cfg['model_list'] if x['model_name'] == 'gpt-6.1-sol')
    rcfg = router['litellm_params']['complexity_router_config']
    assert 'tier_model_params' not in rcfg
    assert rcfg['tier_model_configs']['REASONING'] == [
        {'model_name': 'astra-upstream', 'litellm_params': {'reasoning_effort': 'xhigh'}}
    ]


def test_upstream_lock_is_full_sha_and_records_required_evidence():
    lock = json.loads((ROOT / 'upstream.lock.json').read_text())
    assert lock['litellm']['commit'] == '4bdeb1378bb19a453cd3c49d383ebe76f057d2c6'
    assert len(lock['litellm']['commit']) == 40
    assert lock['litellm']['github_signature_verified'] is True
    assert lock['litellm']['version'] == '1.109.0'
    assert lock['litellm']['subscription_passthrough_merge'] == '2e27a02a9fce9bdc6ece13ba3cb8222dc5b6ecfa'
    assert lock['blocked_artifacts'] == ['litellm==1.107.0']


def test_heavy_smoke_is_manual_and_never_uses_openai_api_key():
    text = (ROOT / '.github/workflows/heavy-smoke.yml').read_text()
    assert 'workflow_dispatch' in text
    assert 'OPENAI_API_KEY' not in text
    assert 'docker compose' in text
    assert '/health/liveliness' in text


def test_phase1_installer_does_not_mutate_codex_config_or_auth():
    text = (ROOT / 'scripts/windows/install.ps1').read_text()
    assert 'RandomNumberGenerator' in text
    assert "Join-Path $env:USERPROFILE '.codex'" not in text
    assert 'auth.json' not in text
    assert text.count('Set-Content -Path') == 1
    assert 'Set-Content -Path $EnvFile' in text
    assert 'docker compose' in text


def test_uninstall_preserves_data_by_default():
    text = (ROOT / 'scripts/windows/uninstall.ps1').read_text()
    assert '[switch]$RemoveData' in text
    assert "docker compose down -v" in text
    assert "docker compose down\n" in text
    assert text.index("if ($RemoveData)") < text.index("docker compose down -v")


def test_preflight_checks_docker_daemon_before_install():
    text = (ROOT / 'scripts/windows/preflight.ps1').read_text()
    assert "docker version" in text
    assert "DockerDaemon" in text
    assert "exit 1" in text


def test_all_yaml_files_parse():
    for path in list(ROOT.rglob('*.yml')) + list(ROOT.rglob('*.yaml')):
        yaml.safe_load(path.read_text())


def test_autorouter_avoids_unknown_external_router_alias():
    cfg = yaml.safe_load((ROOT / 'configs/litellm/autorouter.yaml').read_text())
    names = [x['model_name'] for x in cfg['model_list']]
    assert 'codex-smart-router' not in names
    assert 'gpt-6.1-sol' in names


def test_heavy_smoke_runs_on_tagged_publish_commit_but_not_every_push():
    text = (ROOT / '.github/workflows/heavy-smoke.yml').read_text()
    assert 'push:' in text
    assert "contains(github.event.head_commit.message, '[heavy-smoke]')" in text
    assert "github.event_name == 'workflow_dispatch'" in text


def test_validator_accepts_current_catalog_free_router_contract():
    import importlib.util
    spec = importlib.util.spec_from_file_location('validate_repo', ROOT / 'tools/validate_repo.py')
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    assert module.validate() == []
