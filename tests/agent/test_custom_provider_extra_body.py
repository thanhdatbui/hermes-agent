from types import SimpleNamespace

from agent.agent_init import _merge_custom_provider_extra_body


def test_custom_provider_extra_body_merges_into_request_overrides():
    agent = SimpleNamespace(
        provider="custom",
        model="google/gemma-4-31b-it",
        base_url="https://example.test/v1",
        request_overrides={"service_tier": "priority"},
    )

    _merge_custom_provider_extra_body(
        agent,
        [
            {
                "name": "gemma",
                "base_url": "https://example.test/v1/",
                "model": "google/gemma-4-31b-it",
                "extra_body": {
                    "enable_thinking": True,
                    "reasoning_effort": "high",
                },
            }
        ],
    )

    assert agent.request_overrides == {
        "service_tier": "priority",
        "extra_body": {
            "enable_thinking": True,
            "reasoning_effort": "high",
        },
    }


def test_custom_provider_extra_body_preserves_caller_override():
    agent = SimpleNamespace(
        provider="custom",
        model="google/gemma-4-31b-it",
        base_url="https://example.test/v1",
        request_overrides={
            "extra_body": {
                "reasoning_effort": "low",
                "caller_only": True,
            }
        },
    )

    _merge_custom_provider_extra_body(
        agent,
        [
            {
                "name": "gemma",
                "base_url": "https://example.test/v1",
                "model": "google/gemma-4-31b-it",
                "extra_body": {
                    "enable_thinking": True,
                    "reasoning_effort": "high",
                },
            }
        ],
    )

    assert agent.request_overrides["extra_body"] == {
        "enable_thinking": True,
        "reasoning_effort": "low",
        "caller_only": True,
    }


def test_custom_provider_extra_body_ignores_other_custom_models():
    agent = SimpleNamespace(
        provider="custom",
        model="other-model",
        base_url="https://example.test/v1",
        request_overrides={},
    )

    _merge_custom_provider_extra_body(
        agent,
        [
            {
                "name": "gemma",
                "base_url": "https://example.test/v1",
                "model": "google/gemma-4-31b-it",
                "extra_body": {"enable_thinking": True},
            }
        ],
    )

    assert agent.request_overrides == {}


def test_named_custom_provider_extra_body_matches_provider_key():
    agent = SimpleNamespace(
        provider="custom:zai-coding-plan",
        model="glm-5.2",
        base_url="https://api.z.ai/api/coding/paas/v4",
        request_overrides={},
    )

    _merge_custom_provider_extra_body(
        agent,
        [
            {
                "provider_key": "other-provider",
                "name": "Other Provider",
                "base_url": "https://api.z.ai/api/coding/paas/v4",
                "model": "glm-5.2",
                "extra_body": {"enable_thinking": True},
            },
            {
                "provider_key": "zai-coding-plan",
                "name": "Z.AI Coding Plan",
                "base_url": "https://api.z.ai/api/coding/paas/v4/",
                "model": "glm-5.2",
                "extra_body": {"enable_thinking": False},
            },
        ],
    )

    assert agent.request_overrides == {"extra_body": {"enable_thinking": False}}


def test_live_switch_refreshes_named_custom_request_overrides(monkeypatch):
    """A live switch must carry the target provider's route metadata and use
    the runtime billing class instead of the durable custom menu key."""
    from agent import agent_runtime_helpers as arh

    agent = SimpleNamespace(
        model="old-model",
        provider="openrouter",
        base_url="https://old.example/v1",
        api_mode="chat_completions",
        api_key="old-key",
        client=object(),
        _client_kwargs={"api_key": "old-key", "base_url": "https://old.example/v1"},
        _credential_pool=None,
        _config_context_length=None,
        _custom_providers=[
            {
                "provider_key": "9router",
                "name": "9router",
                "base_url": "http://127.0.0.1:20128/v1",
                "model": "cmc/deepseek/deepseek-v4-flash",
                "extra_body": {"synthetic_route_flag": "preserve"},
            }
        ],
        request_overrides={"extra_body": {"old_route": True}},
        _use_prompt_caching=False,
        _use_native_cache_layout=False,
        reasoning_config=None,
        _fallback_chain=[],
        _fallback_model=None,
        _fallback_activated=False,
        _fallback_index=0,
        _cached_system_prompt="old",
    )
    agent._anthropic_prompt_cache_policy = lambda **_kwargs: (False, False)
    agent._ensure_lmstudio_runtime_loaded = lambda: None
    agent._apply_client_headers_for_base_url = lambda _base_url: None
    agent._create_openai_client = lambda _kwargs, **_kw: object()

    monkeypatch.setattr("agent.credential_pool.load_pool", lambda _provider: None)
    monkeypatch.setattr("agent.chat_completion_helpers._reset_stale_streak", lambda _agent: None)
    monkeypatch.setattr("hermes_cli.config.load_config", lambda: {})

    arh.switch_model(
        agent,
        new_model="cmc/deepseek/deepseek-v4-flash",
        new_provider="custom:9router",
        api_key="new-key",
        base_url="http://127.0.0.1:20128/v1",
        api_mode="chat_completions",
    )

    assert agent.provider == "custom"
    assert agent.request_overrides == {
        "extra_body": {"synthetic_route_flag": "preserve"}
    }
    assert agent._primary_runtime["request_overrides"] == agent.request_overrides

    # If target metadata cannot be resolved but the route is unchanged, the
    # caller-supplied override map must survive the live switch.
    monkeypatch.setattr(arh, "_request_overrides_for_runtime", lambda *args, **kwargs: None)
    arh.switch_model(
        agent,
        new_model="cmc/deepseek/deepseek-v4-flash",
        new_provider="custom:9router",
        api_key="new-key-2",
        base_url="http://127.0.0.1:20128/v1",
        api_mode="chat_completions",
    )
    assert agent.request_overrides == {
        "extra_body": {"synthetic_route_flag": "preserve"}
    }


def test_live_switch_override_resolution_returns_none_when_target_has_no_metadata():
    """An unresolved target must not be represented as an empty override map."""
    from agent import agent_runtime_helpers as arh

    agent = SimpleNamespace(_custom_providers=[])
    assert arh._request_overrides_for_runtime(
        agent,
        requested_provider="custom:missing",
        model="missing-model",
        base_url="http://127.0.0.1:20128/v1",
    ) is None
