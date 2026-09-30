"""Focused unit tests for Telegram multi-ISP send/edit failover transport."""

from unittest.mock import AsyncMock, MagicMock, patch
import httpx
import pytest


async def _fake_deadline(coro, *args, **kwargs): return await coro

from gateway.config import PlatformConfig
from plugins.platforms.telegram.adapter import TelegramAdapter
from plugins.platforms.telegram.telegram_network import TelegramMultiISPTransport


@pytest.mark.asyncio
async def test_telegram_multi_isp_send_and_polling_transports(monkeypatch):
    """Verify both request (send) and get_updates_request (polling) use distinct
    TelegramMultiISPTransport instances when proxy and fallback_ips are present."""
    monkeypatch.setenv("TELEGRAM_PROXY", "http://127.0.0.1:40000")
    cfg = PlatformConfig(
        enabled=True,
        token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
    )
    adapter = TelegramAdapter(cfg)

    created_requests = []

    def mock_httpx_request(**kwargs):
        created_requests.append(kwargs)
        mock_req = MagicMock()
        mock_req.shutdown = AsyncMock()
        return mock_req

    mock_app = MagicMock()
    mock_app.initialize = AsyncMock()
    mock_app.start = AsyncMock()
    mock_app.updater = MagicMock()
    mock_app.updater.start_polling = AsyncMock()
    mock_app.bot = MagicMock()
    mock_app.bot.get_me = AsyncMock(return_value=MagicMock(username="test_bot"))

    mock_builder = MagicMock()
    mock_builder.token.return_value = mock_builder
    mock_builder.request.return_value = mock_builder
    mock_builder.get_updates_request.return_value = mock_builder
    mock_builder.build.return_value = mock_app

    async def _fake_deadline(coro, *args, **kwargs):
        return await coro

    with patch.object(adapter, "_acquire_platform_lock", return_value=True), \
         patch.object(adapter, "_fallback_ips", return_value=["149.154.167.220", "149.154.175.100"]), \
         patch("plugins.platforms.telegram.adapter.HTTPXRequest", side_effect=mock_httpx_request), \
         patch("plugins.platforms.telegram.adapter.Application.builder", return_value=mock_builder), \
         patch("plugins.platforms.telegram.adapter._await_with_thread_deadline", side_effect=_fake_deadline):

        await adapter.connect()

        # Should create 2 HTTPXRequest instances: request and get_updates_request
        assert len(created_requests) >= 2
        send_req_kw, poll_req_kw = created_requests[0], created_requests[1]

        # Both must have transport in httpx_kwargs
        assert "transport" in send_req_kw.get("httpx_kwargs", {})
        assert "transport" in poll_req_kw.get("httpx_kwargs", {})

        send_transport = send_req_kw["httpx_kwargs"]["transport"]
        poll_transport = poll_req_kw["httpx_kwargs"]["transport"]

        assert isinstance(send_transport, TelegramMultiISPTransport)
        assert isinstance(poll_transport, TelegramMultiISPTransport)

        # Must be distinct transport instances so send and poll don't interfere
        assert send_transport is not poll_transport

        # Both configured with discovered fallback IPs
        assert send_transport._fallback_ips == ["149.154.167.220", "149.154.175.100"]
        assert poll_transport._fallback_ips == ["149.154.167.220", "149.154.175.100"]


@pytest.mark.asyncio
async def test_telegram_failover_disabled_uses_plain_proxy(monkeypatch):
    """When HERMES_TELEGRAM_DISABLE_FALLBACK_IPS is set, standard proxy is used."""
    monkeypatch.setenv("TELEGRAM_PROXY", "http://127.0.0.1:40000")
    monkeypatch.setenv("HERMES_TELEGRAM_DISABLE_FALLBACK_IPS", "true")
    cfg = PlatformConfig(
        enabled=True,
        token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
    )
    adapter = TelegramAdapter(cfg)

    created_requests = []

    def mock_httpx_request(**kwargs):
        created_requests.append(kwargs)
        mock_req = MagicMock()
        mock_req.shutdown = AsyncMock()
        return mock_req

    mock_app = MagicMock()
    mock_app.initialize = AsyncMock()
    mock_app.start = AsyncMock()
    mock_app.updater = MagicMock()
    mock_app.updater.start_polling = AsyncMock()
    mock_app.bot = MagicMock()
    mock_app.bot.get_me = AsyncMock(return_value=MagicMock(username="test_bot"))

    mock_builder = MagicMock()
    mock_builder.token.return_value = mock_builder
    mock_builder.request.return_value = mock_builder
    mock_builder.get_updates_request.return_value = mock_builder
    mock_builder.build.return_value = mock_app

    async def _fake_deadline(coro, *args, **kwargs):
        return await coro

    with patch.object(adapter, "_acquire_platform_lock", return_value=True), \
         patch.object(adapter, "_fallback_ips", return_value=["149.154.167.220"]), \
         patch("plugins.platforms.telegram.adapter.HTTPXRequest", side_effect=mock_httpx_request), \
         patch("plugins.platforms.telegram.adapter.Application.builder", return_value=mock_builder), \
         patch("plugins.platforms.telegram.adapter._await_with_thread_deadline", side_effect=_fake_deadline):

        await adapter.connect()

        assert len(created_requests) >= 2
        send_req_kw = created_requests[0]
        assert send_req_kw.get("proxy") == "http://127.0.0.1:40000"
        assert "transport" not in send_req_kw.get("httpx_kwargs", {})


@pytest.mark.asyncio
async def test_telegram_send_path_failover_execution():
    transport = TelegramMultiISPTransport(fallback_ips=["149.154.167.220"])
    primary = MagicMock()
    primary.handle_async_request = AsyncMock(side_effect=httpx.ConnectTimeout("primary down"))
    primary.aclose = AsyncMock()
    fallback = MagicMock()
    fallback.aclose = AsyncMock()
    response = httpx.Response(200, request=httpx.Request("GET", "https://api.telegram.org/"))
    fallback.handle_async_request = AsyncMock(return_value=response)
    transport._primary_transport = primary
    transport._fallback_transport = fallback

    try:
        result = await transport.handle_async_request(response.request)
        assert result is response
        assert transport._current_mode == "fallback"
        primary.handle_async_request.assert_awaited_once()
        fallback.handle_async_request.assert_awaited_once_with(response.request)
    finally:
        await transport.aclose()