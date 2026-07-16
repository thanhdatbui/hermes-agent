"""Register the opt-in Claude Code lane at the Kanban edge."""

from .edge import check_claude_lane, run_claude_lane


def register(ctx) -> None:
    ctx.register_tool(
        name="kanban_claude_lane",
        toolset="kanban",
        schema={
            "type": "function",
            "function": {
                "name": "kanban_claude_lane",
                "description": "Run Claude Code in an isolated Kanban worktree.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "prompt": {"type": "string"}, "workspace": {"type": "string"},
                        "test_commands": {"type": "array", "items": {"type": "string"}},
                        "forbidden_paths": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["prompt", "workspace"],
                },
            },
        },
        handler=run_claude_lane,
        check_fn=check_claude_lane,
        description="Run an isolated, opt-in Claude Code implementation lane.",
    )
