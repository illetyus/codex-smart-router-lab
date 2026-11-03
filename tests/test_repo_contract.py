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
        'gpt-image-2': 'chatgpt/gpt-image-2',
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
        {'model_name': 'astra-upstream', 'litellm_params': {'reasoning_effort': 'high'}}
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
    assert 'OPENAI_API_KEY is prohibited' in text
    assert 'router.env' in text
    assert 'docker compose' in text


def test_uninstall_preserves_data_by_default():
    text = (ROOT / 'scripts/windows/uninstall.ps1').read_text()
    assert '[switch]$RemoveData' in text
    assert "ValidateSet('native','docker')" in text
    assert 'Unregister-ScheduledTask' in text
    assert "docker compose down -v" in text
    assert 'PostgreSQL database is preserved' in text
    assert text.index("if ($RemoveData)") < text.index('Remove-Item -LiteralPath $RuntimeRoot')


def test_preflight_checks_runtime_specific_prerequisites():
    text = (ROOT / 'scripts/windows/preflight.ps1').read_text()
    assert "ValidateSet('native','docker')" in text
    assert "if ($Runtime -eq 'docker')" in text
    assert "docker version" in text
    assert "DockerDaemon" in text
    assert "Test-Command 'uv'" in text
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
        'postgres:16.15-bookworm@sha256:e8a07d2c7579b038938cdba6c539e580e5001caf9ea203d397b5cc83e76bd938'
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
        'critical': {'model': 'gpt-6-astra', 'reasoning_effort': 'high'},
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
        'gpt-image-2': 'chatgpt/gpt-image-2',
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
    assert "'gpt-6.1-sol'" in text
    assert "'codex-*'" in text
    assert "'gpt-image-2'" in text
    for model in ('gpt-6-luna', 'gpt-6.1-terra', 'gpt-6-sol', 'gpt-6-astra'):
        assert model in text
    assert '/key/generate' in text
    assert '/key/info' not in text
    assert '?key=' not in text
    assert '$created.models' in text
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


def test_preflight_checks_powershell_loopback_and_optional_compose():
    text = (ROOT / 'scripts/windows/preflight.ps1').read_text()
    assert 'docker compose version' in text
    assert 'PowerShell7' in text
    assert 'Port4000Available' in text
    assert "if ($Runtime -eq 'docker')" in text
    assert "Test-Command 'pg_isready'" in text


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
    assert tm['REASONING'][0]['litellm_params']['reasoning_effort'] == 'high'


def test_restore_tracks_codex_dotenv_applied_hash_and_conflicts():
    provision = (ROOT / 'scripts/windows/provision-codex-key.ps1').read_text()
    restore = (ROOT / 'scripts/windows/restore-codex-provider.ps1').read_text()
    assert '.env.pre-litellm-applied.sha256' in provision
    assert '.env.pre-litellm-applied.sha256' in restore
    assert 'pre-litellm-restore-conflict' in restore


def test_secret_files_are_acl_hardened_and_virtual_keys_expire():
    install = (ROOT / 'scripts/windows/install.ps1').read_text()
    provision = (ROOT / 'scripts/windows/provision-codex-key.ps1').read_text()
    restore = (ROOT / 'scripts/windows/restore-codex-provider.ps1').read_text()
    assert 'Protect-SecretFile' in install
    assert 'Protect-SecretFile' in provision
    assert 'Protect-SecretFile' in restore
    assert 'SetAccessRuleProtection' in install
    assert 'SetAccessRuleProtection' in provision
    assert "[string]$Duration = '30d'" in provision
    assert 'duration = $Duration' in provision


def test_installer_rejects_placeholder_or_weak_existing_env():
    text = (ROOT / 'scripts/windows/install.ps1').read_text()
    assert 'CHANGE_ME' in text
    assert 'OPENAI_API_KEY' in text
    assert 'existing .env failed validation' in text


def test_virtual_key_revocation_helper_is_present_and_secret_safe():
    path = ROOT / 'scripts/windows/revoke-codex-key.ps1'
    assert path.exists()
    text = path.read_text()
    assert '/key/delete' in text
    assert 'keys = @($virtualKey)' in text
    assert 'LITELLM_MASTER_KEY' in text
    assert 'LITELLM_API_KEY' in text
    assert 'Write-Host $virtualKey' not in text
    assert 'Write-Output $virtualKey' not in text
    assert 'Protect-SecretFile' in text


def test_models_are_config_owned_not_db_mutable():
    compose = yaml.safe_load((ROOT / 'docker-compose.yml').read_text())
    assert compose['services']['litellm']['environment']['STORE_MODEL_IN_DB'] == 'False'


def test_litellm_configs_harden_direct_client_trust_and_key_lifetime():
    for name in ('subscription.yaml', 'model-probe.yaml', 'autorouter.yaml'):
        cfg = yaml.safe_load((ROOT / 'configs/litellm' / name).read_text())
        assert cfg['general_settings']['trusted_proxy_ranges'] == []
        assert cfg['litellm_settings']['upperbound_key_generate_params']['duration'] == '30d'


def test_compose_disables_unused_admin_and_api_documentation_surfaces():
    compose = yaml.safe_load((ROOT / 'docker-compose.yml').read_text())
    env = compose['services']['litellm']['environment']
    assert env['DISABLE_ADMIN_UI'] == 'True'
    assert env['NO_DOCS'] == 'True'
    assert env['NO_REDOC'] == 'True'
    assert env['NO_OPENAPI'] == 'True'


def test_security_docs_record_hardening_and_litellm_release_maturity():
    security = (ROOT / 'docs/SECURITY.md').read_text()
    evidence = (ROOT / 'docs/EVIDENCE.md').read_text()
    assert 'trusted_proxy_ranges' in security
    assert 'DISABLE_ADMIN_UI' in security
    assert 'NO_OPENAPI' in security
    assert 'upperbound_key_generate_params' in security
    assert 'v1.109.0-dev.2' in evidence
    assert 'stable `v1.109.0`' in evidence


def test_status_records_final_hardened_code_checkpoint():
    status = (ROOT / 'docs/STATUS.md').read_text()
    assert '41539957203' in status
    assert '41539957189' in status
    assert '0af84ab3b2a32af43a2d46afe2243259cffd1625' in status
    assert 'repository-side pre-install validation is complete' in status.lower()
    assert 'must pass normal branch CI' not in status


def test_heavy_smoke_proves_management_surface_hardening_and_key_cap():
    workflow = (ROOT / '.github/workflows/heavy-smoke.yml').read_text()
    assert 'Verify hardened management surfaces' in workflow
    # Pinned LiteLLM still serves static /ui assets when the Admin UI is disabled.
    # Prove the server-side disable flag and a protected UI auth endpoint instead.
    assert '/.well-known/litellm-ui-config' in workflow
    assert 'admin_ui_disabled' in workflow
    assert '/sso/key/generate' in workflow
    assert 'Admin UI is Disabled' in workflow
    assert '/openapi.json' in workflow
    assert '/redoc' in workflow
    tool = (ROOT / 'tools/k2_key_smoke.py').read_text()
    assert '31d' in tool
    assert 'HTTPError' in tool
    assert 'virtual-key duration cap' in tool


def test_security_docs_scope_admin_ui_disable_and_keep_sso_unconfigured():
    security = (ROOT / 'docs/SECURITY.md').read_text()
    compose = yaml.safe_load((ROOT / 'docker-compose.yml').read_text())
    env = compose['services']['litellm']['environment']
    for name in ('GOOGLE_CLIENT_ID', 'MICROSOFT_CLIENT_ID', 'GENERIC_CLIENT_ID'):
        assert name not in env
    assert 'source=litellm-cli' in security
    assert 'CLI SSO' in security
    assert 'no SSO provider credentials' in security


def test_native_windows_runtime_files_exist():
    required = [
        'scripts/windows/start-router.ps1',
        'scripts/windows/register-router-task.ps1',
        'scripts/windows/provision-postgres.ps1',
        'docs/NATIVE-WINDOWS.md',
    ]
    missing = [p for p in required if not (ROOT / p).exists()]
    assert not missing, f'missing native Windows files: {missing}'


def test_native_windows_is_default_runtime_and_keeps_docker_optional():
    install = (ROOT / 'scripts/windows/install.ps1').read_text()
    preflight = (ROOT / 'scripts/windows/preflight.ps1').read_text()
    uninstall = (ROOT / 'scripts/windows/uninstall.ps1').read_text()
    for text in (install, preflight, uninstall):
        assert "ValidateSet('native','docker')" in text
        assert "[string]$Runtime = 'native'" in text
    assert "if ($Runtime -eq 'docker')" in install
    assert 'uv sync' in install
    assert 'docker compose' in install


def test_native_installer_pins_source_and_reproduces_docker_python_contract():
    text = (ROOT / 'scripts/windows/install.ps1').read_text()
    assert '4bdeb1378bb19a453cd3c49d383ebe76f057d2c6' in text
    assert 'git checkout --detach' in text
    assert 'uv sync' in text
    assert '--frozen' in text
    assert '--python 3.13' in text
    assert '--extra proxy' in text
    assert '--extra extra_proxy' in text
    assert 'prisma generate' in text
    assert 'schema.prisma' in text


def test_native_preflight_checks_required_tools_without_making_docker_mandatory():
    text = (ROOT / 'scripts/windows/preflight.ps1').read_text()
    for check in ('uv', 'node', 'psql', 'pg_isready'):
        assert f"Test-Command '{check}'" in text
    assert "if ($Runtime -eq 'docker')" in text
    assert 'DockerDaemon' in text


def test_native_launcher_binds_loopback_and_restores_security_environment():
    text = (ROOT / 'scripts/windows/start-router.ps1').read_text()
    assert '--host' in text
    assert '127.0.0.1' in text
    assert '--port' in text
    assert '4000' in text
    for name in (
        'DATABASE_URL', 'LITELLM_MASTER_KEY', 'LITELLM_SALT_KEY',
        'STORE_MODEL_IN_DB', 'DISABLE_ADMIN_UI',
        'NO_DOCS', 'NO_REDOC', 'NO_OPENAPI', 'CHECKPOINT_DISABLE',
    ):
        assert name in text
    assert 'OPENAI_API_KEY is prohibited' in text


def test_native_task_runs_at_logon_and_has_bounded_restart_policy():
    text = (ROOT / 'scripts/windows/register-router-task.ps1').read_text()
    assert 'New-ScheduledTaskAction' in text
    assert 'New-ScheduledTaskTrigger' in text
    assert 'Register-ScheduledTask' in text
    assert 'AtLogOn' in text
    assert 'RestartCount' in text
    assert 'RestartInterval' in text
    assert 'MultipleInstances' in text


def test_native_postgres_provisioner_keeps_database_local_and_secrets_out_of_args():
    text = (ROOT / 'scripts/windows/provision-postgres.ps1').read_text()
    assert "[string]$HostName = '127.0.0.1'" in text
    assert 'RandomNumberGenerator' in text
    assert "$env:PGPASSWORD" in text
    assert '--password' not in text
    assert 'DATABASE_URL' in text
    assert 'Set-DotEnvValue' in text
    assert 'Protect-SecretFile' in text


def test_native_windows_docs_are_primary_user_install_path():
    readme = (ROOT / 'README.md').read_text()
    native = (ROOT / 'docs/NATIVE-WINDOWS.md').read_text()
    assert 'Native Windows' in readme
    assert 'Docker is not required' in readme
    assert 'CI/Heavy Smoke' in readme
    assert 'PostgreSQL 16.15' in native
    assert '127.0.0.1:4000' in native
    assert 'Task Scheduler' in native
    assert 'K2' in native


def test_postgres_ci_image_is_updated_to_current_16_15_bookworm_digest():
    compose = yaml.safe_load((ROOT / 'docker-compose.yml').read_text())
    image = compose['services']['db']['image']
    assert image == 'postgres:16.15-bookworm@sha256:e8a07d2c7579b038938cdba6c539e580e5001caf9ea203d397b5cc83e76bd938'
    lock = json.loads((ROOT / 'upstream.lock.json').read_text())
    assert lock['runtime_dependencies']['postgres_image'] == image


def test_native_launcher_clears_inherited_sso_configuration():
    text = (ROOT / 'scripts/windows/start-router.ps1').read_text()
    for name in (
        'GOOGLE_CLIENT_ID', 'GOOGLE_CLIENT_SECRET',
        'MICROSOFT_CLIENT_ID', 'MICROSOFT_CLIENT_SECRET', 'MICROSOFT_TENANT',
        'GENERIC_CLIENT_ID', 'GENERIC_CLIENT_SECRET',
        'SAML_IDP_METADATA_URL', 'SAML_IDP_METADATA_XML',
    ):
        assert name in text
    assert "SetEnvironmentVariable($ssoName, $null, 'Process')" in text


def test_key_management_prefers_native_gateway_env_with_docker_fallback():
    for name in ('provision-codex-key.ps1', 'revoke-codex-key.ps1'):
        text = (ROOT / 'scripts/windows' / name).read_text()
        assert "[string]$RuntimeRoot = (Join-Path $env:LOCALAPPDATA 'CodexSmartRouter')" in text
        assert "[string]$GatewayEnvPath = ''" in text
        assert "Join-Path $RuntimeRoot 'router.env'" in text
        assert "Join-Path $RepoRoot '.env'" in text
        assert 'Get-DotEnvValue -Path $GatewayEnvPath' in text
