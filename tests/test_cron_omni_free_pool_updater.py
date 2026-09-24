from __future__ import annotations

import json
from pathlib import Path
import sys
from unittest.mock import MagicMock
import urllib.error
import urllib.request
import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "deploy" / "hermes-home" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import cron_omni_free_pool_updater


def test_clean_model_name() -> None:
    # Prefix trimming
    assert cron_omni_free_pool_updater.clean_model_name("openrouter/nex-agi/nex-n2.5-pro:free") == "nex-agi/nex-n2.5-pro"
    assert cron_omni_free_pool_updater.clean_model_name("chatgpt-web/gpt-5.6-luna-free") == "gpt-5.6-luna-free"

    # Suffix trimming
    assert cron_omni_free_pool_updater.clean_model_name("openrouter/nvidia/nemotron-3-super-120b-a12b:free-low") == "nvidia/nemotron-3-super-120b-a12b"
    assert cron_omni_free_pool_updater.clean_model_name("chatgpt-web/gpt-5.6-sol-instant:free") == "gpt-5.6-sol-instant"
    assert cron_omni_free_pool_updater.clean_model_name("test-model:free-low") == "test-model"
    assert cron_omni_free_pool_updater.clean_model_name("test-model:free") == "test-model"

    # Edge cases: no prefix/suffix, empty string
    assert cron_omni_free_pool_updater.clean_model_name("custom-provider/custom-model") == "custom-provider/custom-model"
    assert cron_omni_free_pool_updater.clean_model_name("plain-model") == "plain-model"
    assert cron_omni_free_pool_updater.clean_model_name("") == ""


def test_test_model_liveness_success(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.__enter__.return_value = mock_resp

    mock_urlopen = MagicMock(return_value=mock_resp)
    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    mid = "openrouter/nex-agi/nex-n2.5-pro:free"
    res_mid, dt, ok = cron_omni_free_pool_updater.test_model_liveness(mid)

    assert res_mid == mid
    assert ok is True
    assert dt < 999.0
    assert mock_urlopen.called


def test_test_model_liveness_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(*args, **kwargs):
        raise urllib.error.URLError("Connection refused")

    monkeypatch.setattr(urllib.request, "urlopen", _raise)

    mid = "openrouter/broken-model:free"
    res_mid, dt, ok = cron_omni_free_pool_updater.test_model_liveness(mid)

    assert res_mid == mid
    assert ok is False
    assert dt == 999.0


def test_report_error(capsys: pytest.CaptureFixture) -> None:
    error_msg = "test error message"
    with pytest.raises(SystemExit) as exc_info:
        cron_omni_free_pool_updater.report_error(error_msg)

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "⚡ *[OMNI-FREE] CẬP NHẬT ROUTING POOL*" in captured.out
    assert "• *Trạng thái:* ❌ Thất bại" in captured.out
    assert error_msg in captured.out


def _create_mock_urlopen(verification_error: bool = False):
    def _mock_urlopen(req, *args, **kwargs):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__.return_value = mock_resp

        if "openrouter.ai/api/v1/models" in url:
            catalog = {
                "data": [
                    {
                        "id": "meta-llama/llama-3.3-70b-instruct:free",
                        "pricing": {"prompt": "0", "completion": "0"},
                    },
                    {
                        "id": "google/gemini-3.8-flash:free",
                        "pricing": {"prompt": "0", "completion": "0"},
                    },
                ]
            }
            mock_resp.read.return_value = json.dumps(catalog).encode("utf-8")
            return mock_resp

        if "/api/combos/" in url:
            mock_resp.read.return_value = b'{"status": "updated"}'
            return mock_resp

        if "/v1/chat/completions" in url:
            data = getattr(req, "data", None)
            if data:
                payload = json.loads(data.decode("utf-8"))
                if payload.get("model") == "omni-free":
                    if verification_error:
                        raise TimeoutError("Verification timed out")
                    mock_resp.read.return_value = json.dumps({"model": "test-live-model"}).encode("utf-8")
                    return mock_resp

            mock_resp.read.return_value = json.dumps({
                "choices": [{"message": {"role": "assistant", "content": "pong"}}]
            }).encode("utf-8")
            return mock_resp

        mock_resp.read.return_value = b"{}"
        return mock_resp

    return _mock_urlopen


def test_run_updater_stdout_report_and_stderr_logs(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    mock_urlopen = _create_mock_urlopen(verification_error=False)
    monkeypatch.setattr(cron_omni_free_pool_updater.urllib.request, "urlopen", mock_urlopen)

    cron_omni_free_pool_updater.run_updater()

    captured = capsys.readouterr()

    # stdout verification
    assert "⚡ *[OMNI-FREE] CẬP NHẬT POOL THÀNH CÔNG*" in captured.out
    assert "• *Trạng thái:* ✅ Hoạt động" in captured.out
    assert "Thứ tự ưu tiên (Priority Tiers)" in captured.out
    assert "GPT-5.6 Luna Free" in captured.out
    assert "GPT-5.6 Sol Instant" in captured.out

    assert "[OMNI-FREE-UPDATER]" not in captured.out
    assert "Candidate pool size" not in captured.out
    assert "+ LIVE:" not in captured.out

    # stderr verification
    assert "[OMNI-FREE-UPDATER]" in captured.err


def test_run_updater_verification_ping_timeout_fallback(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    mock_urlopen = _create_mock_urlopen(verification_error=True)
    monkeypatch.setattr(cron_omni_free_pool_updater.urllib.request, "urlopen", mock_urlopen)

    cron_omni_free_pool_updater.run_updater()

    captured = capsys.readouterr()

    # Successful completion despite verification timeout
    assert "⚡ *[OMNI-FREE] CẬP NHẬT POOL THÀNH CÔNG*" in captured.out
    assert "• *Trạng thái:* ✅ Hoạt động" in captured.out
    assert "GPT-5.6 Luna Free" in captured.out
    assert "GPT-5.6 Sol Instant" in captured.out

    # stderr should capture verification warning
    assert "Verification warning" in captured.err
