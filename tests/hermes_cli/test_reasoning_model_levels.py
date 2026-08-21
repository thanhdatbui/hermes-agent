"""Model-aware effort choices for the interactive CLI."""

from hermes_cli.cli_commands_mixin import CLICommandsMixin


class _Stub(CLICommandsMixin):
    def __init__(self, model):
        self.model = model
        self.reasoning_config = None
        self.show_reasoning = True
        self.reasoning_full = False
        self.agent = None

    def _current_reasoning_callback(self):
        return None


def test_deepseek_v4_rejects_generic_effort(capsys):
    stub = _Stub("cmc/deepseek/deepseek-v4-flash")

    stub._handle_reasoning_command("/reasoning medium")

    assert stub.reasoning_config is None
    assert "Valid levels for cmc/deepseek/deepseek-v4-flash: none, low, high, max" in capsys.readouterr().out


def test_deepseek_v4_accepts_native_effort(tmp_path, monkeypatch):
    hermes_home = tmp_path / ".hermes"
    hermes_home.mkdir()
    (hermes_home / "config.yaml").write_text("agent:\n  reasoning_effort: high\n", encoding="utf-8")
    monkeypatch.setenv("HERMES_HOME", str(hermes_home))

    import cli

    monkeypatch.setattr(cli, "_hermes_home", hermes_home, raising=False)
    stub = _Stub("deepseek-v4-flash")

    stub._handle_reasoning_command("/reasoning max")

    assert stub.reasoning_config == {"enabled": True, "effort": "max"}
