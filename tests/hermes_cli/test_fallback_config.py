"""Regression tests for configured fallback route normalization."""

import pytest

from hermes_cli.fallback_config import get_fallback_chain


NINEROUTER_URL = "http://127.0.0.1:20128/v1"
GEMINI_MODEL = "gemini/gemini-3.6-flash"


@pytest.mark.parametrize(
    "provider_config",
    [
        {"custom_providers": [{"name": "9Router", "base_url": NINEROUTER_URL}]},
        {"providers": {"9router": {"api": NINEROUTER_URL}}},
    ],
)
def test_gemini_fallback_uses_named_9router(provider_config):
    config = {
        **provider_config,
        "fallback_model": {"provider": "gemini", "model": GEMINI_MODEL, "base_url": NINEROUTER_URL},
    }

    assert get_fallback_chain(config) == [
        {
            "provider": "custom:9router",
            "model": GEMINI_MODEL,
            "base_url": NINEROUTER_URL,
        }
    ]


def test_gemini_fallback_without_named_9router_is_unchanged():
    entry = {"provider": "gemini", "model": GEMINI_MODEL}

    assert get_fallback_chain({"fallback_model": entry}) == [entry]


def test_explicit_direct_gemini_endpoint_is_unchanged_with_named_9router():
    direct_url = "https://generativelanguage.googleapis.com/v1beta"
    entry = {
        "provider": "gemini",
        "model": GEMINI_MODEL,
        "base_url": direct_url,
    }

    result = get_fallback_chain(
        {
            "custom_providers": [
                {"name": "9router", "base_url": NINEROUTER_URL}
            ],
            "fallback_model": entry,
        }
    )

    assert result == [entry]


def test_explicit_9router_endpoint_gets_canonical_provider_slug():
    entry = {
        "provider": "gemini",
        "model": GEMINI_MODEL,
        "base_url": f"{NINEROUTER_URL}/",
    }

    result = get_fallback_chain(
        {
            "providers": {"9router": {"api": NINEROUTER_URL}},
            "fallback_providers": [entry],
        }
    )

    assert result == [
        {
            "provider": "custom:9router",
            "model": GEMINI_MODEL,
            "base_url": NINEROUTER_URL,
        }
    ]


def test_primary_gemini_config_is_not_mutated():
    config = {
        "model": {"provider": "gemini", "default": GEMINI_MODEL},
        "custom_providers": [{"name": "9router", "base_url": NINEROUTER_URL}],
        "fallback_model": {"provider": "openrouter", "model": "other/model"},
    }

    get_fallback_chain(config)

    assert config["model"] == {"provider": "gemini", "default": GEMINI_MODEL}
