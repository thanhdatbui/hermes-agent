from pathlib import Path


SKILL = Path(__file__).resolve().parents[2] / "skills" / "autonomous-ai-agents" / "kanban-computer-use-lane" / "SKILL.md"


def test_computer_use_lane_reuses_existing_surfaces() -> None:
    source = SKILL.read_text(encoding="utf-8")
    for token in ("computer-use-lane-v1", "computer_use", "kanban_show", "kanban_heartbeat", "kanban_complete", "kanban_block"):
        assert token in source
    assert "second desktop automation process" in source


def test_computer_use_lane_keeps_only_loop_bounds() -> None:
    source = SKILL.read_text(encoding="utf-8").lower()
    assert "finite task runtime and retry budget" in source
    assert "adds no action policy" in source
    assert "repeat the same capture/action pair" in source
