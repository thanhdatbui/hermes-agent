from __future__ import annotations

import os
from typing import Any

from providers import register_provider
from providers.base import ProviderProfile

FARM_MODELS: tuple[str, ...] = (
    "omni-worker",
    "omni-free",
    "ag-gemini-pool-3",
    "ag-claude",
    "ag-opus",
)


class OmniProfile(ProviderProfile):
    """OmniRoute — forwards reasoning_effort to control thinking budget."""

    def fetch_models(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 8.0,
    ) -> list[str] | None:
        """Chặn live discovery tới :20129/v1/models; ép dùng fallback_models."""
        return None

    def build_api_kwargs_extras(
        self, *, reasoning_config: dict | None = None, model: str | None = None, **context
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        extra_body: dict[str, Any] = {}
        top_level: dict[str, Any] = {}

        if isinstance(reasoning_config, dict):
            enabled = reasoning_config.get("enabled", True)
            effort = (reasoning_config.get("effort") or "").strip().lower()
            if not enabled or effort == "none":
                top_level["reasoning_effort"] = "none"
            elif effort in {"low", "medium", "high", "max"}:
                top_level["reasoning_effort"] = effort

        return extra_body, top_level


omni = OmniProfile(
    name="omni",
    aliases=("omniroute",),
    display_name="OmniRoute",
    description="OmniRoute local proxy with priority combo routing",
    signup_url="",
    env_vars=("OMNIROUTE_API_KEY", "OMNIROUTE_BASE_URL"),
    base_url=os.getenv("OMNIROUTE_BASE_URL", "http://192.168.110.123:20129/v1").rstrip("/"),
    models_url="",
    auth_type="api_key",
    supports_health_check=True,
    supports_vision=True,
    supports_vision_tool_messages=True,
    fallback_models=FARM_MODELS,
    hostname="127.0.0.1",
    default_headers={},
    fixed_temperature=None,
    default_max_tokens=65536,
    default_aux_model="",
    api_mode="chat_completions",
)

register_provider(omni)
