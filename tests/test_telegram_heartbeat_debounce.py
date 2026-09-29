from __future__ import annotations

import sys
import json
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
import pytest

PLUGIN_DIR = Path(__file__).resolve().parent.parent / "plugins" / "platforms" / "telegram"
if str(PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR))

import telegram_network  # noqa: E402
import adapter  # noqa: E402


def test_proxy_error_is_retryable_connect_error():
    assert telegram_network._is_retryable_connect_error(httpx.ConnectTimeout("timeout")) is True
    assert telegram_network._is_retryable_connect_error(httpx.ConnectError("connect error")) is True
    assert telegram_network._is_retryable_connect_error(httpx.ProxyError("proxy unreachable")) is True
    assert telegram_network._is_retryable_connect_error(httpx.ReadTimeout("read timeout")) is False
    assert telegram_network._is_retryable_connect_error(ValueError("value error")) is False


def test_adapter_debounce_code_contract():
    adapter_path = PLUGIN_DIR / "adapter.py"
    assert adapter_path.exists()
    content = adapter_path.read_text(encoding="utf-8")

    # 1. Assert fail_count reset on success
    assert "self._polling_heartbeat_fail_count = 0" in content

    # 2. Assert debounce 3 consecutive failures
    assert "_polling_heartbeat_fail_count >= 3" in content
    assert "heartbeat probe (3 consecutive failures)" in content

    # 3. Assert fast retry 15s when fail_count > 0
    assert 'sleep_s = 15 if getattr(self, "_polling_heartbeat_fail_count", 0) > 0 else HEARTBEAT_INTERVAL' in content

    # 4. Assert telemetry audit log environment config and non-silent error handling
    assert "TELEGRAM_AUDIT_LOG_DIR" in content
    assert "telegram_gateway_audit.jsonl" in content
    assert "Failed to write telegram gateway audit log" in content


@pytest.mark.asyncio
async def test_telegram_adapter_real_loop_transient_failure_and_recovery():
    """Chạy trực tiếp method _polling_heartbeat_loop trên TelegramAdapter thật để kiểm chứng 2 kịch bản:
    1. Lỗi transient (1-2 lần) rồi thành công -> KHÔNG kích hoạt recovery.
    2. Lỗi liên tiếp 3 lần -> Kích hoạt recovery đúng 1 lần.
    """
    adapter_obj = adapter.TelegramAdapter.__new__(adapter.TelegramAdapter)
    adapter_obj.platform = type("MockP", (), {"value": "telegram"})()
    adapter_obj._fatal_error_message = None
    adapter_obj._polling_teardown_started = False
    adapter_obj._polling_heartbeat_fail_count = 0
    adapter_obj._polling_error_task = None
    adapter_obj._background_tasks = set()
    adapter_obj._schedule_polling_recovery = MagicMock()
    adapter_obj._probe_pending_updates = AsyncMock()

    mock_bot = MagicMock()
    adapter_obj._app = MagicMock()
    adapter_obj._app.bot = mock_bot

    # Kịch bản 1: Fail 2 lần, lần 3 thành công -> KHÔNG kích hoạt recovery
    mock_bot.get_me = AsyncMock(side_effect=[
        asyncio.TimeoutError("transient err 1"),
        OSError("transient err 2"),
        MagicMock(id=123, username="bot"),  # Success
    ])

    ticks = 0
    async def fast_sleep_scenario1(s):
        nonlocal ticks
        ticks += 1
        if ticks > 3:
            adapter_obj._polling_teardown_started = True

    with patch.object(adapter.asyncio, "sleep", side_effect=fast_sleep_scenario1):
        await adapter_obj._polling_heartbeat_loop()

    assert adapter_obj._polling_heartbeat_fail_count == 0  # Đã reset về 0 khi get_me thành công
    assert adapter_obj._schedule_polling_recovery.call_count == 0  # Chưa đủ 3 lần fail

    # Kịch bản 2: Fail liên tiếp 3 lần -> BẮT BUỘC kích hoạt recovery ở lần thứ 3
    adapter_obj._polling_teardown_started = False
    adapter_obj._polling_heartbeat_fail_count = 0
    mock_bot.get_me = AsyncMock(side_effect=[
        asyncio.TimeoutError("err 1"),
        asyncio.TimeoutError("err 2"),
        asyncio.TimeoutError("err 3"),
    ])

    ticks2 = 0
    sleep_intervals = []
    async def fast_sleep_scenario2(s):
        nonlocal ticks2
        sleep_intervals.append(s)
        ticks2 += 1
        if ticks2 > 3:
            adapter_obj._polling_teardown_started = True

    with patch.object(adapter.asyncio, "sleep", side_effect=fast_sleep_scenario2):
        await adapter_obj._polling_heartbeat_loop()

    assert adapter_obj._schedule_polling_recovery.call_count == 1
    call_args = adapter_obj._schedule_polling_recovery.call_args
    assert "3 consecutive failures" in call_args.kwargs.get("reason", "")
    assert isinstance(call_args.args[0], asyncio.TimeoutError)

    # Xác thực adaptive sleep cadence trong kịch bản 2:
    # Lần 1: fail_count=0 -> sleep HEARTBEAT_INTERVAL (180s từ .env hoặc 30s default)
    # Lần 2 & 3: fail_count>0 -> sleep 15s (fast retry)
    assert sleep_intervals[0] in [30, 180]
    assert sleep_intervals[1] == 15
    assert sleep_intervals[2] == 15


@pytest.mark.asyncio
async def test_telegram_adapter_telemetry_audit_logging_contract(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Kiểm chứng _schedule_polling_recovery phát telemetry event vào file audit JSONL cô lập trong tmp_path."""
    monkeypatch.setenv("TELEGRAM_AUDIT_LOG_DIR", str(tmp_path))

    adapter_obj = adapter.TelegramAdapter.__new__(adapter.TelegramAdapter)
    adapter_obj.platform = type("MockP", (), {"value": "telegram"})()
    adapter_obj._fatal_error_message = None
    adapter_obj._polling_teardown_started = False
    adapter_obj._polling_error_task = None
    adapter_obj._background_tasks = set()
    # Mock coroutine để tránh warning coroutine was never awaited
    adapter_obj._handle_polling_network_error = AsyncMock()

    coro_to_await = None
    def fake_create_task(coro):
        nonlocal coro_to_await
        coro_to_await = coro
        task = MagicMock()
        task.done.return_value = False
        return task

    with patch.object(adapter.asyncio, "get_running_loop") as mock_loop:
        mock_loop.return_value.create_task.side_effect = fake_create_task

        adapter_obj._schedule_polling_recovery(
            OSError("Connection lost"),
            reason="heartbeat probe (3 consecutive failures)"
        )

    if coro_to_await:
        await coro_to_await

    audit_file = tmp_path / "telegram_gateway_audit.jsonl"
    assert audit_file.exists()
    lines = audit_file.read_text(encoding="utf-8", errors="ignore").splitlines()
    assert len(lines) == 1
    last_log = json.loads(lines[0].strip())
    assert last_log["event"] == "POLLING_RECOVERY_SCHEDULED"
    assert "3 consecutive failures" in last_log["reason"]
    assert "Connection lost" in last_log["error"]
    assert "timestamp" in last_log
