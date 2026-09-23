from __future__ import annotations

from pathlib import Path
import sys
from unittest.mock import MagicMock
import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "deploy" / "hermes-home" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import tiktok_runner  # noqa: E402

_original_is_file = Path.is_file


def _mock_is_file(self: Path) -> bool:
    if "ensure_row_accounts" in str(self):
        return True
    return _original_is_file(self)


def test_preflight_kibe(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Path, "is_file", _mock_is_file)
    mock_run = MagicMock()
    monkeypatch.setattr(tiktok_runner.subprocess, "run", mock_run)

    state_file = tmp_path / "runner.json"
    cluster = {
        "name": "kibe",
        "state_file": state_file,
        "host_config": "kibe.yaml",
    }
    window_key = "2026-09-24_10"

    tiktok_runner._preflight_ensure_accounts(row=3, window_key=window_key, cluster=cluster)

    marker = tmp_path / f".preflight_kibe_{window_key}"
    assert marker.exists()
    assert mock_run.called
    args, kwargs = mock_run.call_args
    assert kwargs.get("env") is not None
    assert kwargs["env"].get("TAADAA_HOST_CONFIG") == "kibe.yaml"
    assert kwargs["env"].get("ADB_SERVER_SOCKET") is None or "ADB_SERVER_SOCKET" not in cluster


def test_preflight_admin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Path, "is_file", _mock_is_file)
    mock_run = MagicMock()
    monkeypatch.setattr(tiktok_runner.subprocess, "run", mock_run)

    state_file = tmp_path / "runner.json"
    cluster = {
        "name": "admin",
        "state_file": state_file,
        "host_config": "admin.yaml",
        "adb_server_socket": "tcp:192.168.110.119:5037",
    }
    window_key = "2026-09-24_11"

    tiktok_runner._preflight_ensure_accounts(row=5, window_key=window_key, cluster=cluster)

    marker = tmp_path / f".preflight_admin_{window_key}"
    assert marker.exists()
    assert mock_run.called
    args, kwargs = mock_run.call_args
    assert kwargs.get("env") is not None
    assert kwargs["env"].get("TAADAA_HOST_CONFIG") == "admin.yaml"
    assert kwargs["env"].get("ADB_SERVER_SOCKET") == "tcp:192.168.110.119:5037"


def test_preflight_marker_exists_skips(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Path, "is_file", _mock_is_file)
    mock_run = MagicMock()
    monkeypatch.setattr(tiktok_runner.subprocess, "run", mock_run)

    state_file = tmp_path / "runner.json"
    cluster = {
        "name": "kibe",
        "state_file": state_file,
        "host_config": "kibe.yaml",
    }
    window_key = "2026-09-24_12"

    marker = tmp_path / f".preflight_kibe_{window_key}"
    marker.write_text("existing", encoding="utf-8")

    tiktok_runner._preflight_ensure_accounts(row=3, window_key=window_key, cluster=cluster)

    assert not mock_run.called
    assert marker.read_text(encoding="utf-8") == "existing"
