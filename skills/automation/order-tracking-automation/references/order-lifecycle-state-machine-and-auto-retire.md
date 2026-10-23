# Order Lifecycle State Machine and Terminal Auto-Retire Pattern

## Overview

Taadaa Phone Farm manages real TikTok Shop merchandise orders placed across farm devices. To balance order tracking accuracy against farm operations (device locking, video rendering, feed sessions), tracking is governed by a strict 3-phase state machine with automatic retirement and pure-script watchdog execution.

## The 3-Phase State Machine

```text
[New Order Created]
        │
        ▼
┌────────────────────────────────────────────────────────┐
│ Phase 1: NEED_APP_SYNC (In-App TikTok Discovery)       │
│ • Conditions: `tracking_code is None` or `carrier` unassigned  │
│ • Execution:                                           │
│   - Check `operator_device_lock(serial, timeout=10)`   │
│   - If device busy with feed/cron: defer politely      │
│   - If acquired: wake device, launch TikTok            │
│   - Switch account via Canonical `account_switcher`    │
│   - Open "Đơn hàng của bạn" / TikTok Shop              │
│   - Tab Trap: if "Không có đơn hàng", tap "Tất cả"     │
│   - Tap tracking banner -> Detail screen               │
│   - WinRT OCR extracts: carrier, tracking_code, status │
│   - Save screenshot `order_{id}_app.jpg`               │
│   - Sync `orders.json` & Excel                         │
└───────────────────────┬────────────────────────────────┘
                        │ tracking_code obtained
                        ▼
┌────────────────────────────────────────────────────────┐
│ Phase 2: ACTIVE_WEB_TRACKING (Zero-ADB Web/API Poller) │
│ • Conditions: `tracking_code` present, not terminal    │
│ • Execution:                                           │
│   - STRICTLY ZERO PHONE / ADB INTERACTION              │
│   - Phone released immediately for farm feed/video     │
│   - Poll carrier Web API every 10–15m:                 │
│     * J&T: `https://jtexpress.vn/vi/tracking?type=...` │
│       with `billcode` + `cellphone={phone_last4}`      │
│     * SPX: `https://spx.vn/api/v2/fleet_order/...`     │
│     * Ninja Van: `https://api.ninjavan.co/vn/...`      │
│   - Events:                                            │
│     * Shipper out for delivery -> update status        │
│     * Arrived at Da Nang hub -> send pickup alert      │
└───────────────────────┬────────────────────────────────┘
                        │ Signed / Delivered / Cancelled
                        ▼
┌────────────────────────────────────────────────────────┐
│ Phase 3: TERMINAL / RETIRED (Completed & Archived)     │
│ • Status: "Đã giao hàng thành công (Đã ký nhận)",      │
│   "Đã ký nhận", "Hoàn thành", "Đã hủy"                 │
│ • Execution:                                           │
│   - Final sync of recipient name and delivery timestamp│
│   - Send completion alert (Telegram / Voice)           │
│   - AUTOMATICALLY RETIRE FROM ACTIVE TRACKING QUEUE    │
│   - Subsequent runs skip 100%: 0 ADB, 0 Web calls,     │
│     0 log noise                                        │
│   - Retained statically in DB/Excel for Dashboard :1905│
└────────────────────────────────────────────────────────┘
```

## Critical Invariants

1. **Terminal Auto-Retire:** Any order whose status matches `TERMINAL_STATUSES` must be ignored unconditionally in subsequent execution cycles. Never poll carriers for already-delivered parcels.
2. **Pure Script Watchdog (`no_agent: true`):** Never configure order tracking cron jobs as LLM agents. An LLM agent consumes API quota, introduces model latency, and fails loudly with HTTP 503 errors when local proxies (9Router/OmniRoute) face pre-dispatch filter spikes. Deploy watchdogs with `no_agent: true` running deterministic Python that stays completely silent when no state change occurs.
3. **UI Boundary Enforcement:**
   - **Native Shell (Account Switcher):** Always use Canonical XML module (`automation_core.tiktok.account_switcher`) to ensure 100% exact handle matching (`@tooanh2604`, `@augustusdant7`).
   - **WebViews / Shop / Detail Screens:** Always use WinRT OCR Primary (`automation_core.ocr` / `ui_extract`) to reliably extract tracking codes and carrier labels from rendered pixels.
