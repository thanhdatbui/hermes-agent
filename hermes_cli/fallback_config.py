"""Helpers for reading the effective fallback provider chain from config."""

from __future__ import annotations

from typing import Any

from hermes_cli.config import get_compatible_custom_providers
from hermes_cli.providers import custom_provider_slug


_GEMINI_PROVIDER_NAMES = frozenset(
    {"gemini", "google", "google-gemini", "google-ai-studio"}
)
_NINEROUTER_PROVIDER_SLUG = "custom:9router"
_CUSTOM_PROVIDER_ROUTING_FIELDS = ("name", "base_url", "url", "api")


def _custom_provider_routing_config(config: dict[str, Any]) -> dict[str, Any]:
    """Build a credential-free view for custom-provider identity lookup."""
    routing_config: dict[str, Any] = {}

    raw_custom_providers = config.get("custom_providers")
    if isinstance(raw_custom_providers, list):
        routing_config["custom_providers"] = [
            {
                key: entry[key]
                for key in _CUSTOM_PROVIDER_ROUTING_FIELDS
                if key in entry
            }
            for entry in raw_custom_providers
            if isinstance(entry, dict)
        ]

    raw_providers = config.get("providers")
    if isinstance(raw_providers, dict):
        routing_config["providers"] = {
            str(provider_key): {
                key: entry[key]
                for key in _CUSTOM_PROVIDER_ROUTING_FIELDS
                if key in entry
            }
            for provider_key, entry in raw_providers.items()
            if isinstance(entry, dict)
        }

    return routing_config


def _configured_9router(config: dict[str, Any]) -> tuple[str, str] | None:
    """Return the canonical 9Router slug and endpoint when configured.

    Use the shared custom-provider compatibility view so both the keyed
    ``providers:`` schema and the legacy ``custom_providers:`` list work.  We
    intentionally inspect only provider identity and endpoint here; fallback
    normalization must not resolve or copy credentials.
    """
    try:
        entries = get_compatible_custom_providers(
            _custom_provider_routing_config(config)
        )
    except Exception:
        return None

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        identities = (
            entry.get("name"),
            entry.get("provider_key"),
        )
        if not any(
            custom_provider_slug(str(identity or "")) == _NINEROUTER_PROVIDER_SLUG
            for identity in identities
        ):
            continue
        base_url = _normalized_base_url(entry.get("base_url"))
        if base_url:
            return _NINEROUTER_PROVIDER_SLUG, base_url
    return None


def _canonicalize_gemini_fallback(
    entry: dict[str, Any],
    configured_9router: tuple[str, str] | None,
) -> dict[str, Any]:
    """Route an implicit Gemini fallback through a configured 9Router entry.

    A fallback entry with its own endpoint is explicit intent. Preserve it
    unless it already points at the configured 9Router endpoint, in which case
    upgrading the provider label makes the named custom route durable too.
    Primary/explicit Gemini configuration is outside this helper's scope.
    """
    if configured_9router is None:
        return entry

    provider = str(entry.get("provider") or "").strip().lower()
    if provider not in _GEMINI_PROVIDER_NAMES:
        return entry

    configured_provider, configured_base_url = configured_9router
    entry_base_url = _normalized_base_url(entry.get("base_url"))
    if entry_base_url and entry_base_url.lower() != configured_base_url.lower():
        return entry

    # Explicit Gemini without an explicit endpoint stays direct.
    if not entry_base_url:
        return entry

    normalized = dict(entry)
    normalized["provider"] = configured_provider
    normalized["base_url"] = configured_base_url
    return normalized


def _normalized_base_url(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip().rstrip("/")


def _iter_fallback_entries(raw: Any) -> list[dict[str, Any]]:
    if isinstance(raw, dict):
        candidates = [raw]
    elif isinstance(raw, list):
        candidates = raw
    else:
        return []

    entries: list[dict[str, Any]] = []
    for entry in candidates:
        if not isinstance(entry, dict):
            continue
        provider = str(entry.get("provider") or "").strip()
        model = str(entry.get("model") or "").strip()
        if not provider or not model:
            continue

        normalized = dict(entry)
        normalized["provider"] = provider
        normalized["model"] = model

        base_url = _normalized_base_url(entry.get("base_url"))
        if base_url:
            normalized["base_url"] = base_url

        entries.append(normalized)
    return entries


def _entry_identity(entry: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(entry.get("provider") or "").strip().lower(),
        str(entry.get("model") or "").strip().lower(),
        _normalized_base_url(entry.get("base_url")).lower(),
    )


def get_fallback_chain(config: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Return the effective fallback chain merged across old and new config keys.

    ``fallback_providers`` remains the primary source of truth and keeps its
    order. Legacy ``fallback_model`` entries are appended afterwards unless
    they target the same provider/model/base_url route as an earlier entry.
    The returned list always contains fresh dict copies. An implicit Gemini
    fallback is upgraded to ``custom:9router`` only when the config defines a
    named 9Router endpoint; explicit Gemini endpoints remain unchanged.
    """

    config = config or {}
    chain: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    configured_9router = _configured_9router(config)

    for key in ("fallback_providers", "fallback_model"):
        for entry in _iter_fallback_entries(config.get(key)):
            entry = _canonicalize_gemini_fallback(entry, configured_9router)
            identity = _entry_identity(entry)
            if identity in seen:
                continue
            seen.add(identity)
            chain.append(entry)

    return chain
