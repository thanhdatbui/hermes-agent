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


def test_env_var_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    custom_combo_id = "test-custom-combo-uuid"
    custom_base_url = "http://127.0.0.1:29999"
    custom_conn_id = "test-custom-conn-uuid"

    monkeypatch.setenv("OMNI_FREE_COMBO_ID", custom_combo_id)
    monkeypatch.setenv("OMNI_BASE_URL", custom_base_url)
    monkeypatch.setenv("OPENROUTER_CONN_ID", custom_conn_id)

    import importlib
    importlib.reload(cron_omni_free_pool_updater)

    try:
        assert cron_omni_free_pool_updater.COMBO_ID == custom_combo_id
        assert cron_omni_free_pool_updater.OMNI_BASE == custom_base_url
        assert cron_omni_free_pool_updater.OR_CONN_ID == custom_conn_id

        captured_requests = []

        def _mock_urlopen(req, *args, **kwargs):
            url = req.full_url if hasattr(req, "full_url") else str(req)
            captured_requests.append((url, req))
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock_resp.__enter__.return_value = mock_resp
            if "openrouter.ai" in url:
                mock_resp.read.return_value = b'{"data": []}'
            elif "/api/combos/" in url:
                mock_resp.read.return_value = b'{"status": "updated"}'
            elif "/v1/chat/completions" in url:
                mock_resp.read.return_value = b'{"model": "test"}'
            return mock_resp

        monkeypatch.setattr(cron_omni_free_pool_updater.urllib.request, "urlopen", _mock_urlopen)
        monkeypatch.setattr(cron_omni_free_pool_updater, "test_model_liveness", lambda mid: (mid, 0.5, True))

        cron_omni_free_pool_updater.run_updater()

        patch_calls = [req for url, req in captured_requests if "/api/combos/" in url]
        assert len(patch_calls) == 1
        assert patch_calls[0].full_url == f"{custom_base_url}/api/combos/{custom_combo_id}"
        patch_data = json.loads(patch_calls[0].data.decode("utf-8"))
        openrouter_items = [m for m in patch_data["models"] if m["providerId"] == "openrouter"]
        assert len(openrouter_items) > 0
        for m in openrouter_items:
            assert m["connectionId"] == custom_conn_id
    finally:
        monkeypatch.undo()
        importlib.reload(cron_omni_free_pool_updater)


def test_run_updater_zero_live_models_fallback(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    captured_patch_payload = {}

    def _mock_urlopen(req, *args, **kwargs):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__.return_value = mock_resp

        if "openrouter.ai" in url:
            mock_resp.read.return_value = b'{"data": []}'
            return mock_resp
        if "/api/combos/" in url:
            captured_patch_payload.update(json.loads(req.data.decode("utf-8")))
            mock_resp.read.return_value = b'{"status": "updated"}'
            return mock_resp
        if "/v1/chat/completions" in url:
            mock_resp.read.return_value = json.dumps({"model": "chatgpt-web/gpt-5.6-luna-free"}).encode("utf-8")
            return mock_resp
        return mock_resp

    monkeypatch.setattr(cron_omni_free_pool_updater.urllib.request, "urlopen", _mock_urlopen)
    monkeypatch.setattr(cron_omni_free_pool_updater, "test_model_liveness", lambda mid: (mid, 999.0, False))

    cron_omni_free_pool_updater.run_updater()

    captured = capsys.readouterr()

    # Verify PATCH payload has only the 2 ChatGPT Web fallback models
    assert len(captured_patch_payload.get("models", [])) == 2
    models = captured_patch_payload["models"]
    assert models[0]["model"] == "chatgpt-web/gpt-5.6-luna-free"
    assert models[1]["model"] == "chatgpt-web/gpt-5.6-sol-instant"

    # Verify stdout report shows success and Web Fallback
    assert "⚡ *[OMNI-FREE] CẬP NHẬT POOL THÀNH CÔNG*" in captured.out
    assert "• *Trạng thái:* ✅ Hoạt động" in captured.out
    assert "Web Fallback" in captured.out
    assert "0 OpenRouter + 2 ChatGPT Web" in captured.out
    assert "GPT-5.6 Luna Free" in captured.out
    assert "GPT-5.6 Sol Instant" in captured.out


def test_patch_payload_schema_and_integrity(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_payload = {}

    def _mock_urlopen(req, *args, **kwargs):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__.return_value = mock_resp

        if "openrouter.ai" in url:
            mock_resp.read.return_value = b'{"data": []}'
            return mock_resp
        if "/api/combos/" in url:
            captured_payload.update(json.loads(req.data.decode("utf-8")))
            mock_resp.read.return_value = b'{"status": "updated"}'
            return mock_resp
        if "/v1/chat/completions" in url:
            mock_resp.read.return_value = json.dumps({"model": "test"}).encode("utf-8")
            return mock_resp
        return mock_resp

    monkeypatch.setattr(cron_omni_free_pool_updater.urllib.request, "urlopen", _mock_urlopen)
    monkeypatch.setattr(cron_omni_free_pool_updater, "test_model_liveness", lambda mid: (mid, 0.45, True))

    cron_omni_free_pool_updater.run_updater()

    assert captured_payload.get("strategy") == "priority"
    config = captured_payload.get("config", {})
    assert config.get("maxRetries") == 1
    assert config.get("retryDelayMs") == 100
    assert config.get("targetTimeoutMs") == 25000
    assert config.get("failoverBeforeRetry") is True

    models = captured_payload.get("models", [])
    assert len(models) >= 2
    for m in models:
        assert "id" in m and isinstance(m["id"], str)
        assert "kind" in m and m["kind"] == "model"
        assert "model" in m and isinstance(m["model"], str)
        assert "providerId" in m and m["providerId"] in ("openrouter", "chatgpt-web")
        if m["providerId"] == "openrouter":
            assert "connectionId" in m and m["connectionId"] == cron_omni_free_pool_updater.OR_CONN_ID
        assert "weight" in m and isinstance(m["weight"], int)
        assert "label" in m and isinstance(m["label"], str)


def test_structured_telemetry_emission(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    mock_urlopen = _create_mock_urlopen(verification_error=False)
    monkeypatch.setattr(cron_omni_free_pool_updater.urllib.request, "urlopen", mock_urlopen)

    cron_omni_free_pool_updater.run_updater()

    captured = capsys.readouterr()
    assert '[TELEMETRY_METRIC] {"event": "omni_free_pool_updated"' in captured.err

    telemetry_line = None
    for line in captured.err.splitlines():
        if line.startswith("[TELEMETRY_METRIC] "):
            telemetry_line = line[len("[TELEMETRY_METRIC] "):]
            break

    assert telemetry_line is not None
    data = json.loads(telemetry_line)
    assert data["event"] == "omni_free_pool_updated"
    assert "timestamp" in data
    assert "total_tiers" in data
    assert "openrouter_live_count" in data
    assert "top_model" in data
    assert "models" in data and isinstance(data["models"], list)


def test_openrouter_catalog_filters(monkeypatch: pytest.MonkeyPatch) -> None:
    catalog_sample = [
        # Free valid model
        {
            "id": "meta-llama/llama-3.3-70b-instruct:free",
            "pricing": {"prompt": "0", "completion": "0"},
        },
        # Paid model (should be skipped)
        {
            "id": "openai/gpt-4o",
            "pricing": {"prompt": "0.005", "completion": "0.015"},
        },
        # Gemini 3.8 variants (should be skipped)
        {
            "id": "google/gemini-3.8-flash:free",
            "pricing": {"prompt": "0", "completion": "0"},
        },
        {
            "id": "google/gemini-2.5-flash-3.8-flash:free",
            "pricing": {"prompt": "0", "completion": "0"},
        },
        # Content safety / moderation models (should be skipped)
        {
            "id": "meta-llama/llama-guard-3-8b-content-safety:free",
            "pricing": {"prompt": "0", "completion": "0"},
        },
        {
            "id": "openai/omni-moderation-latest:free",
            "pricing": {"prompt": "0", "completion": "0"},
        },
        # Another valid free model with numeric float zero
        {
            "id": "mistralai/mistral-7b-instruct:free",
            "pricing": {"prompt": 0.0, "completion": 0.0},
        },
        # Invalid / missing pricing
        {
            "id": "unknown/broken-model",
            "pricing": {"prompt": "invalid"},
        },
    ]

    filtered = cron_omni_free_pool_updater.filter_catalog_models(catalog_sample)

    assert "openrouter/meta-llama/llama-3.3-70b-instruct:free" in filtered
    assert "openrouter/mistralai/mistral-7b-instruct:free" in filtered
    assert "openrouter/openai/gpt-4o" not in filtered
    assert "openrouter/google/gemini-3.8-flash:free" not in filtered
    assert "openrouter/google/gemini-2.5-flash-3.8-flash:free" not in filtered
    assert "openrouter/meta-llama/llama-guard-3-8b-content-safety:free" not in filtered
    assert "openrouter/openai/omni-moderation-latest:free" not in filtered
    assert len(filtered) == 2
