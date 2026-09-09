from __future__ import annotations

from typing import Any

from providers import register_provider
from providers.base import ProviderProfile


class OmniProfile(ProviderProfile):
    """OmniRoute — forwards reasoning_effort to control thinking budget."""

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
    env_vars=("OMNIROUTE_API_KEY",),
    base_url="http://127.0.0.1:20129/v1",
    models_url="",
    auth_type="api_key",
    supports_health_check=True,
    supports_vision=True,
    supports_vision_tool_messages=True,
    fallback_models=(),
    hostname="127.0.0.1",
    default_headers={},
    fixed_temperature=None,
    default_max_tokens=65536,
    default_aux_model="",
    api_mode="chat_completions",
)

register_provider(omni)
