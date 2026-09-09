"""Telegram-specific network helpers.

Provides a hostname-preserving fallback transport for networks where
api.telegram.org resolves to an endpoint that is unreachable from the current
host. The transport keeps the logical request host and TLS SNI as
api.telegram.org while retrying the TCP connection against one or more fallback
IPv4 addresses.
"""

from __future__ import annotations

import asyncio
import contextlib
import ipaddress
import logging
import socket
import time
from typing import Iterable, Optional

import httpx

logger = logging.getLogger(__name__)

_TELEGRAM_API_HOST = "api.telegram.org"

# DNS-over-HTTPS providers used to discover Telegram API IPs that may differ
# from the (potentially unreachable) IP returned by the local system resolver.
_DOH_TIMEOUT = 4.0  # seconds — bounded so connect() isn't noticeably delayed

_DOH_PROVIDERS: list[dict] = [
    {
        "url": "https://dns.google/resolve",
        "params": {"name": _TELEGRAM_API_HOST, "type": "A"},
        "headers": {},
    },
    {
        "url": "https://cloudflare-dns.com/dns-query",
        "params": {"name": _TELEGRAM_API_HOST, "type": "A"},
        "headers": {"Accept": "application/dns-json"},
    },
]

# Last-resort IPs when DoH is also blocked.  These are stable Telegram Bot API
# endpoints in the 149.154.160.0/20 block (same seed used by OpenClaw).
_SEED_FALLBACK_IPS: list[str] = ["149.154.166.110", "149.154.167.220"]


def _resolve_proxy_url(target_hosts=None) -> str | None:
    # Delegate to shared implementation (env vars + macOS system proxy detection)
    from gateway.platforms.base import resolve_proxy_url
    return resolve_proxy_url("TELEGRAM_PROXY", target_hosts=target_hosts)


class TelegramFallbackTransport(httpx.AsyncBaseTransport):
    """Retry Telegram Bot API requests via fallback IPs while preserving TLS/SNI.

    Requests continue to target https://api.telegram.org/... logically, but on
    connect failures the underlying TCP connection is retried against a known
    reachable IP. This is effectively the programmatic equivalent of
    ``curl --resolve api.telegram.org:443:<ip>``.
    """

    def __init__(self, fallback_ips: Iterable[str], **transport_kwargs):
        self._fallback_ips = list(dict.fromkeys(_normalize_fallback_ips(fallback_ips)))
        proxy_url = _resolve_proxy_url(target_hosts=[_TELEGRAM_API_HOST, *self._fallback_ips])
        if proxy_url and "proxy" not in transport_kwargs:
            transport_kwargs["proxy"] = proxy_url
        self._primary = httpx.AsyncHTTPTransport(**transport_kwargs)
        self._fallbacks = {
            ip: httpx.AsyncHTTPTransport(**transport_kwargs) for ip in self._fallback_ips
        }
        self._sticky_ip: Optional[str] = None
        self._sticky_lock = asyncio.Lock()

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        if request.url.host != _TELEGRAM_API_HOST or not self._fallback_ips:
            return await self._primary.handle_async_request(request)

        sticky_ip = self._sticky_ip
        attempt_order: list[Optional[str]] = [sticky_ip] if sticky_ip else [None]
        if sticky_ip:
            attempt_order.append(None)  # retry primary DNS after sticky failure
        for ip in self._fallback_ips:
            if ip != sticky_ip:
                attempt_order.append(ip)

        last_error: Exception | None = None
        for ip in attempt_order:
            candidate = request if ip is None else _rewrite_request_for_ip(request, ip)
            transport = self._primary if ip is None else self._fallbacks[ip]
            try:
                response = await transport.handle_async_request(candidate)
                if ip is not None and self._sticky_ip != ip:
                    async with self._sticky_lock:
                        if self._sticky_ip != ip:
                            self._sticky_ip = ip
                            logger.warning(
                                "[Telegram] Primary api.telegram.org path unreachable; using sticky fallback IP %s",
                                ip,
                            )
                return response
            except Exception as exc:
                last_error = exc
                if not _is_retryable_connect_error(exc):
                    raise
                if ip is not None and ip == self._sticky_ip:
                    async with self._sticky_lock:
                        if self._sticky_ip == ip:
                            self._sticky_ip = None
                            logger.warning(
                                "[Telegram] Sticky fallback IP %s failed; resetting to primary DNS path",
                                ip,
                            )
                if ip is None:
                    logger.warning(
                        "[Telegram] Primary api.telegram.org connection failed (%s); trying fallback IPs %s",
                        exc,
                        ", ".join(self._fallback_ips),
                    )
                    continue
                logger.warning("[Telegram] Fallback IP %s failed: %s", ip, exc)
                continue

        if last_error is None:
            raise RuntimeError("All Telegram fallback IPs exhausted but no error was recorded")
        raise last_error

    async def aclose(self) -> None:
        await self._primary.aclose()
        for transport in self._fallbacks.values():
            await transport.aclose()


class TelegramMultiISPTransport(httpx.AsyncBaseTransport):
    """Multi-ISP Failover transport: Viettel Proxy (primary) ↔ FPT Direct (fallback).

    Khi primary bị lỗi kết nối (ConnectTimeout/ConnectError), tự động switch sang
    FPT Direct + DoH fallback IPs. Background probe phục hồi về primary sau 60s.

    Cấu hình qua .env:
      TELEGRAM_PROXY          = primary proxy URL (Viettel: 192.168.110.2:10001)
      TELEGRAM_FAILOVER_STALL_THRESHOLD   = giây trước khi coi là stall (default 20)
      TELEGRAM_FAILOVER_PROBE_INTERVAL    = giây giữa các probe primary recovery (default 60)
    """

    def __init__(
        self,
        *,
        fallback_ips: Iterable[str],
        stall_threshold_s: float = 20.0,
        recovery_probe_interval_s: float = 60.0,
        **transport_kwargs,
    ):
        self._fallback_ips = list(dict.fromkeys(_normalize_fallback_ips(fallback_ips)))
        self._stall_threshold_s = stall_threshold_s
        self._recovery_probe_interval_s = recovery_probe_interval_s
        self._transport_kwargs = dict(transport_kwargs)

        self._mode_lock = asyncio.Lock()
        self._current_mode: str = "primary"  # "primary" | "fallback"
        self._recovery_task: Optional[asyncio.Task] = None
        self._last_primary_success: Optional[float] = None

        # Transports — built lazily to pick up env at init time
        self._primary_transport: Optional[httpx.AsyncHTTPTransport] = None
        self._fallback_transport: Optional["_TelegramDirectFallbackTransport"] = None

    def _build_primary_transport(self) -> httpx.AsyncHTTPTransport:
        """Primary: Viettel proxy (via TELEGRAM_PROXY env)."""
        proxy_url = _resolve_proxy_url(target_hosts=[_TELEGRAM_API_HOST, *self._fallback_ips])
        if proxy_url:
            kwargs = dict(self._transport_kwargs)
            kwargs["proxy"] = proxy_url
            return httpx.AsyncHTTPTransport(**kwargs)
        return httpx.AsyncHTTPTransport(**self._transport_kwargs)

    def _build_fallback_transport(self) -> "_TelegramDirectFallbackTransport":
        """Fallback: FPT Direct + DoH IPs (no proxy — uses TelegramFallbackTransport without proxy)."""
        # Build without proxy by temporarily clearing TELEGRAM_PROXY via a wrapper
        # that passes no proxy kwarg, relying on TelegramFallbackTransport's
        # direct connection to _fallback_ips
        kwargs = dict(self._transport_kwargs)
        # Don't pass proxy — we want direct FPT connection
        return _TelegramDirectFallbackTransport(self._fallback_ips, **kwargs)

    def _get_primary(self) -> httpx.AsyncHTTPTransport:
        if self._primary_transport is None:
            self._primary_transport = self._build_primary_transport()
        return self._primary_transport

    def _get_fallback(self) -> "_TelegramDirectFallbackTransport":
        if self._fallback_transport is None:
            self._fallback_transport = self._build_fallback_transport()
        return self._fallback_transport

    async def _switch_to_fallback(self) -> None:
        async with self._mode_lock:
            if self._current_mode == "fallback":
                return
            self._current_mode = "fallback"
        logger.warning(
            "[Telegram] Multi-ISP Failover: PRIMARY (Viettel) bị lỗi → chuyển sang FALLBACK (FPT Direct)"
        )

    async def _switch_to_primary(self) -> None:
        async with self._mode_lock:
            if self._current_mode == "primary":
                return
            self._current_mode = "primary"
        logger.warning(
            "[Telegram] Multi-ISP Failover: PRIMARY (Viettel) hồi phục → chuyển về PRIMARY"
        )

    async def _probe_primary_recovery(self) -> None:
        """Background task: probe primary mỗi recovery_probe_interval_s giây."""
        first_success_at: Optional[float] = None
        while True:
            await asyncio.sleep(self._recovery_probe_interval_s)
            if self._current_mode != "fallback":
                return  # đã về primary, dừng probe

            try:
                req = httpx.Request("GET", f"https://{_TELEGRAM_API_HOST}/")
                resp = await self._get_primary().handle_async_request(req)
                if 200 <= resp.status_code < 500:
                    now = time.monotonic()
                    if first_success_at is None:
                        first_success_at = now
                        logger.info("[Telegram] Multi-ISP: Primary probe thành công lần 1, chờ thêm %ds", self._recovery_probe_interval_s)
                    else:
                        # 2 lần thành công → switch về primary
                        await self._switch_to_primary()
                        return
                else:
                    first_success_at = None
            except Exception as exc:
                logger.debug("[Telegram] Multi-ISP: Primary probe thất bại: %s", exc)
                first_success_at = None

    def _ensure_recovery_probe(self) -> None:
        if self._recovery_task is None or self._recovery_task.done():
            self._recovery_task = asyncio.create_task(self._probe_primary_recovery())

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        if self._current_mode == "fallback":
            return await self._get_fallback().handle_async_request(request)

        # Primary mode
        try:
            response = await self._get_primary().handle_async_request(request)
            self._last_primary_success = time.monotonic()
            return response
        except Exception as exc:
            if not _is_retryable_connect_error(exc):
                raise
            # Stall / ConnectError → failover
            await self._switch_to_fallback()
            self._ensure_recovery_probe()
            return await self._get_fallback().handle_async_request(request)

    async def aclose(self) -> None:
        if self._primary_transport:
            await self._primary_transport.aclose()
        if self._fallback_transport:
            await self._fallback_transport.aclose()
        if self._recovery_task and not self._recovery_task.done():
            self._recovery_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._recovery_task


class _TelegramDirectFallbackTransport(httpx.AsyncBaseTransport):
    """FPT Direct transport: không dùng proxy, fallback qua DoH IPs."""

    def __init__(self, fallback_ips: Iterable[str], **transport_kwargs):
        self._fallback_ips = list(dict.fromkeys(_normalize_fallback_ips(fallback_ips)))
        # Explicitly remove proxy to go direct via FPT
        kwargs = {k: v for k, v in transport_kwargs.items() if k != "proxy"}
        self._primary = httpx.AsyncHTTPTransport(**kwargs)
        self._fallbacks = {
            ip: httpx.AsyncHTTPTransport(**kwargs) for ip in self._fallback_ips
        }
        self._sticky_ip: Optional[str] = None
        self._sticky_lock = asyncio.Lock()

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        if request.url.host != _TELEGRAM_API_HOST or not self._fallback_ips:
            return await self._primary.handle_async_request(request)

        attempt_order: list[Optional[str]] = [None]
        for ip in self._fallback_ips:
            attempt_order.append(ip)

        last_error: Exception | None = None
        for ip in attempt_order:
            candidate = request if ip is None else _rewrite_request_for_ip(request, ip)
            transport = self._primary if ip is None else self._fallbacks[ip]
            try:
                return await transport.handle_async_request(candidate)
            except Exception as exc:
                last_error = exc
                if not _is_retryable_connect_error(exc):
                    raise
                logger.warning("[Telegram] FPT Direct: %s failed: %s", ip or "direct", exc)
                continue

        if last_error is None:
            raise RuntimeError("FPT Direct: all attempts exhausted")
        raise last_error

    async def aclose(self) -> None:
        await self._primary.aclose()
        for t in self._fallbacks.values():
            await t.aclose()


def _normalize_fallback_ips(values: Iterable[str]) -> list[str]:
    normalized: list[str] = []
    for value in values:
        raw = str(value).strip()
        if not raw:
            continue
        try:
            addr = ipaddress.ip_address(raw)
        except ValueError:
            logger.warning("Ignoring invalid Telegram fallback IP: %r", raw)
            continue
        if addr.version != 4:
            logger.warning("Ignoring non-IPv4 Telegram fallback IP: %s", raw)
            continue
        if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_unspecified:
            logger.warning("Ignoring private/internal Telegram fallback IP: %s", raw)
            continue
        normalized.append(str(addr))
    return normalized


def parse_fallback_ip_env(value: str | None) -> list[str]:
    if not value:
        return []
    parts = [part.strip() for part in value.split(",")]
    return _normalize_fallback_ips(parts)


def _resolve_system_dns() -> set[str]:
    """Return the IPv4 addresses that the OS resolver gives for api.telegram.org."""
    try:
        results = socket.getaddrinfo(_TELEGRAM_API_HOST, 443, socket.AF_INET)
        return {str(addr[4][0]) for addr in results}
    except Exception:
        return set()


async def _query_doh_provider(
    client: httpx.AsyncClient, provider: dict
) -> list[str]:
    """Query one DoH provider and return A-record IPs."""
    try:
        resp = await client.get(
            provider["url"], params=provider["params"], headers=provider["headers"]
        )
        resp.raise_for_status()
        data = resp.json()
        ips: list[str] = []
        for answer in data.get("Answer", []):
            if answer.get("type") != 1:  # A record
                continue
            raw = answer.get("data", "").strip()
            try:
                ipaddress.ip_address(raw)
                ips.append(raw)
            except ValueError:
                continue
        return ips
    except Exception as exc:
        logger.debug("DoH query to %s failed: %s", provider["url"], exc)
        return []


async def discover_fallback_ips() -> list[str]:
    """Auto-discover Telegram API IPs via DNS-over-HTTPS.

    Resolves api.telegram.org through Google and Cloudflare DoH and returns all
    unique A records.  IPs that match the local system resolver are kept rather
    than excluded: in many networks the system-DNS IP is the most reliable path
    to api.telegram.org and a transient primary-path failure should be retried
    against the same address via the IP-rewrite path before the seed list is
    consulted (#14520).  Falls back to a hardcoded seed list only when DoH
    yields no usable answers.
    """
    async with httpx.AsyncClient(timeout=httpx.Timeout(_DOH_TIMEOUT)) as client:
        doh_tasks = [_query_doh_provider(client, p) for p in _DOH_PROVIDERS]
        system_dns_task = asyncio.ensure_future(asyncio.to_thread(_resolve_system_dns))
        results = await asyncio.gather(*doh_tasks, return_exceptions=True)

    system_ips: set[str] = set()
    try:
        system_result = await asyncio.wait_for(system_dns_task, timeout=_DOH_TIMEOUT)
        if isinstance(system_result, set):
            system_ips = system_result
    except Exception:
        logger.debug("System-DNS resolution for %s did not complete in time", _TELEGRAM_API_HOST)

    doh_ips: list[str] = []
    for r in results:
        if isinstance(r, list):
            doh_ips.extend(r)

    seen: set[str] = set()
    candidates: list[str] = []
    for ip in doh_ips:
        if ip not in seen:
            seen.add(ip)
            candidates.append(ip)

    validated = _normalize_fallback_ips(candidates)

    if validated:
        logger.debug("Discovered Telegram fallback IPs via DoH: %s", ", ".join(validated))
        return validated

    logger.info(
        "DoH discovery yielded no usable IPs (system DNS: %s); using seed fallback IPs %s",
        ", ".join(system_ips) or "unknown",
        ", ".join(_SEED_FALLBACK_IPS),
    )
    return list(_SEED_FALLBACK_IPS)


def _rewrite_request_for_ip(request: httpx.Request, ip: str) -> httpx.Request:
    original_host = request.url.host or _TELEGRAM_API_HOST
    url = request.url.copy_with(host=ip)
    headers = request.headers.copy()
    headers["host"] = original_host
    extensions = dict(request.extensions)
    extensions["sni_hostname"] = original_host
    return httpx.Request(
        method=request.method,
        url=url,
        headers=headers,
        stream=request.stream,
        extensions=extensions,
    )


def _is_retryable_connect_error(exc: Exception) -> bool:
    return isinstance(exc, (httpx.ConnectTimeout, httpx.ConnectError))
