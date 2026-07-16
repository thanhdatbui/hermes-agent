"""Register the opt-in Codex lane without extending Hermes core tools."""

from .edge import check_codex_lane, run_codex_lane


def register(ctx) -> None:
    ctx.register_tool(
        name="kanban_codex_lane",
        toolset="kanban",
        schema={
            "type": "function",
            "function": {
                "name": "kanban_codex_lane",
                "description": "Run Codex in an isolated worktree for this Kanban task.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "prompt": {"type": "string"},
                        "workspace": {"type": "string"},
                        "test_commands": {"type": "array", "items": {"type": "string"}},
                        "forbidden_paths": {"type": "array", "items": {"type": "string"}},
                        "mode": {"type": "string", "enum": ["exec", "goal"]},
                    },
                    "required": ["prompt", "workspace"],
                },
            },
        },
        handler=run_codex_lane,
        check_fn=check_codex_lane,
        description="Run an isolated, opt-in Codex implementation lane.",
        emoji="",
    )
