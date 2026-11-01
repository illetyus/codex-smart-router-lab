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
        '.github/workflows/ci.yml', 'tools/validate_repo.py', 'docs/K2-WINDOWS.md', 'docs/K4-ROUTING.md', 'docs/K5-ESCALATION.md',
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
    routes = {m['model_name']: m['litellm_params']['model'] for m in models}
    assert routes == {
        'gpt-6.1-sol': 'chatgpt/gpt-6.1-sol',
        'codex-*': 'chatgpt/codex-*',
    }
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
    upstreams = [x for x in models if x['model_name'].endswith('-upstream')]
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


def test_ci_compose_render_supplies_disposable_required_env():
    text = (ROOT / '.github/workflows/ci.yml').read_text()
    assert 'LITELLM_MASTER_KEY=sk-ci-render-only' in text
    assert 'LITELLM_SALT_KEY=sk-ci-render-salt-only' in text
    assert 'POSTGRES_PASSWORD=ci-render-only' in text
    assert 'docker compose config --quiet' in text


def test_subscription_and_autorouter_preserve_codex_review_passthrough():
    sub = yaml.safe_load((ROOT / 'configs/litellm/subscription.yaml').read_text())
    auto = yaml.safe_load((ROOT / 'configs/litellm/autorouter.yaml').read_text())
    for cfg in (sub, auto):
        routes = {m['model_name']: m['litellm_params']['model'] for m in cfg['model_list']}
        assert routes['codex-*'] == 'chatgpt/codex-*'


def test_k2_runbook_restricts_key_to_baseline_and_review_routes():
    text = (ROOT / 'docs/K2-WINDOWS.md').read_text()
    assert 'gpt-6.1-sol' in text
    assert 'codex-*' in text
    assert 'Do not set `env_key`' in text
    assert 'OPENAI_API_KEY' in text
    assert 'Reply with exactly Hello. Do not use tools.' in text


def test_heavy_smoke_executes_real_autorouter_dry_run():
    text = (ROOT / '.github/workflows/heavy-smoke.yml').read_text()
    assert '/auto_router/test_routing' in (ROOT / 'tools/router_dry_run.py').read_text()
    assert 'python tools/router_dry_run.py' in text
    assert 'sk-ci-only-not-a-real-secret' in text

def test_supply_chain_refs_are_immutable():
    compose = yaml.safe_load((ROOT / 'docker-compose.yml').read_text())
    assert compose['services']['db']['image'] == (
        'postgres:16.10-bookworm@sha256:38471f330eb885e04de130b768d6db4e10469e2311879c7e5c699f6d2d8a1c74'
    )
    for workflow in ('.github/workflows/ci.yml', '.github/workflows/heavy-smoke.yml'):
        text = (ROOT / workflow).read_text()
        assert 'actions/checkout@v4' not in text
        assert 'actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1' in text
    ci = (ROOT / '.github/workflows/ci.yml').read_text()
    assert 'actions/setup-python@v5' not in ci
    assert 'actions/setup-python@6d4fd22b20465ccc0f7354476588e8df7c9ca0e0' in ci


def test_upstream_lock_pins_codex_and_superpowers_evidence():
    lock = json.loads((ROOT / 'upstream.lock.json').read_text())
    assert lock['codex']['commit'] == '67f0994b532b8740f14b5b738af7b7b2a915b1d6'
    assert lock['superpowers']['commit'] == '2ce8aa15d05bd57213e6f746f953aafb7ded7a8b'
    ci = (ROOT / '.github/workflows/ci.yml').read_text()
    assert 'model: Option<String>' in ci
    assert 'reasoning_effort: Option<ReasoningEffort>' in ci
    assert 'Always specify the model explicitly when dispatching a subagent.' in ci
    assert 'Rounds 4-5' in ci

def test_autorouter_exposes_direct_known_models_for_explicit_superpowers_workers():
    cfg = yaml.safe_load((ROOT / 'configs/litellm/autorouter.yaml').read_text())
    routes = {
        m['model_name']: m['litellm_params']['model']
        for m in cfg['model_list']
        if m['model_name'] in {'gpt-6-luna', 'gpt-6.1-terra', 'gpt-6-sol', 'gpt-6-astra'}
    }
    assert routes == {
        'gpt-6-luna': 'chatgpt/gpt-6-luna',
        'gpt-6.1-terra': 'chatgpt/gpt-6.1-terra',
        'gpt-6-sol': 'chatgpt/gpt-6-sol',
        'gpt-6-astra': 'chatgpt/gpt-6-astra',
    }

    # gpt-6.1-sol remains the controller-facing Auto Router, not a direct worker route.
    sol61 = [m for m in cfg['model_list'] if m['model_name'] == 'gpt-6.1-sol']
    assert len(sol61) == 1
    assert sol61[0]['litellm_params']['model'] == 'auto_router/complexity_router'

def test_k4_runbook_keeps_internal_aliases_private():
    text = (ROOT / 'docs/K4-ROUTING.md').read_text()
    for model in ('gpt-6.1-sol', 'gpt-6-luna', 'gpt-6.1-terra', 'gpt-6-sol', 'gpt-6-astra', 'codex-*'):
        assert model in text
    assert 'Do not grant `*-upstream`' in text
    assert 'spawn_agent' in text
    assert 'reasoning_effort' in text

def test_escalation_policy_matches_superpowers_fix_loop():
    cfg = yaml.safe_load((ROOT / 'configs/routing/escalation-policy.yaml').read_text())
    assert cfg['worker_tiers'] == {
        'mechanical': {'model': 'gpt-6-luna', 'reasoning_effort': 'medium'},
        'integration': {'model': 'gpt-6.1-terra', 'reasoning_effort': 'medium'},
        'difficult': {'model': 'gpt-6-sol', 'reasoning_effort': 'high'},
        'critical': {'model': 'gpt-6-astra', 'reasoning_effort': 'xhigh'},
    }
    assert cfg['fix_loop']['rounds_1_3']['action'] == 'retry_same_worker'
    assert cfg['fix_loop']['rounds_4_5']['action'] == 'fresh_worker_promote_one_tier'
    assert cfg['fix_loop']['after_round_5']['action'] == 'breaker_controller_review'
    assert 'verbose_failed_reasoning_trajectory' in cfg['handoff']['discard']


def test_k5_does_not_claim_generic_posttooluse_failure_detection():
    text = (ROOT / 'docs/K5-ESCALATION.md').read_text()
    assert 'does **not** provide a stable top-level' in text
    assert 'issue #34289' in text
    assert 'fresh' in text
    assert 'rounds 4–5' in text


def test_windows_verify_accepts_key_from_codex_dotenv():
    text = (ROOT / 'scripts/windows/verify.ps1').read_text()
    assert "[string]$CodexHome" in text
    assert "$CodexEnvFile = Join-Path $CodexHome '.env'" in text
    assert "Get-Content -Path $CodexEnvFile" in text
    assert "LITELLM_API_KEY" in text
    assert "\\s*LITELLM_API_KEY\\s*=\\s*.+" in text
    assert "process environment only" not in text.lower()


def test_heavy_smoke_proves_restricted_k2_virtual_key_contract():
    tool = ROOT / 'tools/k2_key_smoke.py'
    assert tool.exists(), 'missing K2 virtual-key smoke tool'
    text = tool.read_text()
    assert '/key/generate' in text
    assert '/key/info' in text
    assert '?key=' in text
    assert 'bearer=master_key' in text
    assert 'bearer=virtual_key' not in text
    assert 'gpt-6.1-sol' in text
    assert 'codex-*' in text
    assert '/responses' not in text
    workflow = (ROOT / '.github/workflows/heavy-smoke.yml').read_text()
    assert 'python tools/k2_key_smoke.py' in workflow


def test_k3_model_probe_mode_exists_before_autorouter():
    probe_path = ROOT / 'configs/litellm/model-probe.yaml'
    assert probe_path.exists(), 'missing router-free K3 model probe config'
    cfg = yaml.safe_load(probe_path.read_text())
    routes = {m['model_name']: m['litellm_params']['model'] for m in cfg['model_list']}
    assert routes == {
        'gpt-6.1-sol': 'chatgpt/gpt-6.1-sol',
        'gpt-6-luna': 'chatgpt/gpt-6-luna',
        'gpt-6.1-terra': 'chatgpt/gpt-6.1-terra',
        'gpt-6-sol': 'chatgpt/gpt-6-sol',
        'gpt-6-astra': 'chatgpt/gpt-6-astra',
        'codex-*': 'chatgpt/codex-*',
    }
    serialized = json.dumps(cfg)
    assert 'auto_router/' not in serialized
    assert 'openai/' not in serialized
    assert 'OPENAI_API_KEY' not in serialized

    installer = (ROOT / 'scripts/windows/install.ps1').read_text()
    assert "ValidateSet('subscription','model-probe','autorouter')" in installer
    assert "'model-probe' { 'model-probe.yaml' }" in installer

    heavy = (ROOT / '.github/workflows/heavy-smoke.yml').read_text()
    assert 'Restart with router-free model probe config' in heavy
    assert 'CODEX_ROUTER_CONFIG=model-probe.yaml' in heavy
    assert (ROOT / 'docs/K3-MODEL-PROBE.md').exists()


def test_heavy_smoke_serializes_expensive_source_builds():
    text = (ROOT / '.github/workflows/heavy-smoke.yml').read_text()
    assert 'concurrency:' in text
    assert 'group: codex-smart-router-heavy-smoke' in text
    assert 'cancel-in-progress: true' in text


def test_windows_key_provisioner_is_phase_scoped_and_secret_safe():
    path = ROOT / 'scripts/windows/provision-codex-key.ps1'
    assert path.exists(), 'missing Windows Codex key provisioner'
    text = path.read_text()
    assert "[ValidateSet('k2','k3','runtime')]" in text
    assert "'gpt-6.1-sol', 'codex-*'" in text
    for model in ('gpt-6-luna', 'gpt-6.1-terra', 'gpt-6-sol', 'gpt-6-astra'):
        assert model in text
    assert '/key/generate' in text
    assert '/key/info' in text
    assert 'Write-Host $virtualKey' not in text
    assert 'Write-Output $virtualKey' not in text
    assert 'LITELLM_API_KEY=' in text
    assert "-Name 'LITELLM_MASTER_KEY'" in text
    assert '$replacement = "LITELLM_API_KEY=$virtualKey"' in text


def test_windows_codex_provider_configurator_and_restore_contract():
    configure = ROOT / 'scripts/windows/configure-codex-provider.ps1'
    restore = ROOT / 'scripts/windows/restore-codex-provider.ps1'
    assert configure.exists(), 'missing Codex provider configurator'
    assert restore.exists(), 'missing Codex provider restore helper'

    c = configure.read_text()
    assert "config.toml.pre-litellm-backup" in c
    assert 'model_provider = "litellm_subscription"' in c
    assert '[model_providers.litellm_subscription]' in c
    assert 'base_url = "http://127.0.0.1:4000/v1"' in c
    assert 'wire_api = "responses"' in c
    assert 'requires_openai_auth = true' in c
    assert 'x-litellm-api-key' in c
    assert 'env_key' not in c
    assert 'auth.json' not in c

    r = restore.read_text()
    assert "config.toml.pre-litellm-backup" in r
    assert ".env.pre-litellm-backup" in r
    assert 'auth.json' not in r


def test_codex_image_route_is_explicitly_preserved_everywhere():
    for name in ('subscription.yaml', 'model-probe.yaml', 'autorouter.yaml'):
        cfg = yaml.safe_load((ROOT / 'configs/litellm' / name).read_text())
        routes = {m['model_name']: m['litellm_params']['model'] for m in cfg['model_list']}
        assert routes['gpt-image-2'] == 'chatgpt/gpt-image-2'


def test_runtime_key_profile_matches_public_router_surface():
    text = (ROOT / 'scripts/windows/provision-codex-key.ps1').read_text()
    assert "'runtime'" in text
    for model in ('gpt-6.1-sol', 'gpt-6-luna', 'gpt-6.1-terra', 'gpt-6-sol', 'gpt-6-astra', 'gpt-image-2', 'codex-*'):
        assert model in text


def test_preflight_checks_compose_powershell_and_loopback_port():
    text = (ROOT / 'scripts/windows/preflight.ps1').read_text()
    assert 'docker compose version' in text
    assert 'PowerShell7' in text
    assert 'Port4000Available' in text


def test_heavy_smoke_checks_readiness_not_only_liveliness():
    text = (ROOT / '.github/workflows/heavy-smoke.yml').read_text()
    assert '/health/readiness' in text


def test_router_policy_is_wired_into_a_codex_agents_template():
    policy = ROOT / 'configs/codex/AGENTS.smart-router.md'
    assert policy.exists()
    text = policy.read_text()
    assert 'gpt-6-luna' in text
    assert 'gpt-6.1-terra' in text
    assert 'gpt-6-sol' in text
    assert 'gpt-6-astra' in text
    assert 'rounds 4' in text.lower()
    assert 'reasoning_effort' in text
    assert 'PreToolUse' in text
    assert '#49736' in text


def test_policy_installer_and_restore_are_present_and_managed_block_safe():
    install = ROOT / 'scripts/windows/configure-smart-router-policy.ps1'
    restore = ROOT / 'scripts/windows/restore-smart-router-policy.ps1'
    assert install.exists()
    assert restore.exists()
    itext = install.read_text()
    rtext = restore.read_text()
    assert 'CODEX-SMART-ROUTER:BEGIN' in itext
    assert 'CODEX-SMART-ROUTER:END' in itext
    assert 'CODEX-SMART-ROUTER:BEGIN' in rtext
    assert 'CODEX-SMART-ROUTER:END' in rtext


def test_restore_detects_post_install_config_drift_before_overwrite():
    configure = (ROOT / 'scripts/windows/configure-codex-provider.ps1').read_text()
    restore = (ROOT / 'scripts/windows/restore-codex-provider.ps1').read_text()
    assert 'config.toml.pre-litellm-applied.sha256' in configure
    assert 'config.toml.pre-litellm-applied.sha256' in restore
    assert 'pre-litellm-restore-conflict' in restore


def test_autorouter_declares_effort_for_each_controller_tier():
    cfg = yaml.safe_load((ROOT / 'configs/litellm/autorouter.yaml').read_text())
    router = next(x for x in cfg['model_list'] if x['model_name'] == 'gpt-6.1-sol')
    tm = router['litellm_params']['complexity_router_config']['tier_model_configs']
    assert tm['SIMPLE'][0]['litellm_params']['reasoning_effort'] in {'low','medium','high'}
    assert tm['MEDIUM'][0]['litellm_params']['reasoning_effort'] in {'low','medium','high'}
    assert tm['COMPLEX'][0]['litellm_params']['reasoning_effort'] in {'low','medium','high','xhigh'}
    assert tm['REASONING'][0]['litellm_params']['reasoning_effort'] == 'xhigh'
