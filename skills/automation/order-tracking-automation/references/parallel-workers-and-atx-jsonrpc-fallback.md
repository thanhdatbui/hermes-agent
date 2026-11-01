# Parallel Workers, ATX-Agent JSON-RPC Fallback & Multi-Phase Cadence

## 1. Parallel App Sync vs Sequential Blocking Trap (Max Workers = 15)
- **The Pitfall:** Iterating over `NEED_APP_SYNC` orders sequentially with `max_app_syncs = 1` and early `break` creates severe head-of-line blocking. If the first device (e.g. Machine 2) encounters a popup or delay, all subsequent orders (Machines 3, 4, 5, 6...) starve indefinitely and never get inspected.
- **The Invariant:** When multiple farm devices have pending orders, execute Phase 1 concurrently across devices using `concurrent.futures.ThreadPoolExecutor(max_workers=min(15, len(pending)))`. Each thread binds to a single independent farm device.
- **Thread-Safety:** Protect all file writes to `orders.json` and `QuanLyDonHang_TikTokShop.xlsx` with a process-level `threading.Lock()` to prevent race conditions when multiple workers complete simultaneously.

## 2. ATX-Agent JSON-RPC (Port 7912) vs Banned Shell UiAutomator Dump
- **Farm Invariant:** Shell `uiautomator dump` (`/system/bin/uiautomator dump`) and `uiautomator2` library imports are **STRICTLY PROHIBITED** across the entire farm. On Samsung Galaxy S7 (Android 7/8, RAM 4GB), shell dump triggers kernel OOM kills (`EXIT 137`), hangs the USB bus, and terminates background TikTok sessions.
- **Two-Layer Hierarchy:**
  1. **Primary (Vision-First):** WinRT OCR (`winrt_ocr_util`) directly on device screenshot (< 0.2s, Zero phone CPU).
  2. **Fallback (Daemon-Level JSON-RPC):** When WinRT OCR misses tracking numbers due to font styling or webview elements, query the ATX-Agent daemon running on port 7912 via `automation_core.persistent_ui.capture_atx_session_ui(adb)`. This uses the in-process `dumpWindowHierarchy` JSON-RPC endpoint, completely avoiding shell process spawning and OOM kills.

## 3. Strict Two-Phase Schedule Separation
- **Phase 2 (Web API Carrier Tracking):**
  - Carrier APIs (J&T, GHN, SPX) query purely over Internet (< 1.5s total, **Zero ADB**).
  - Must run frequently during daytime hours (e.g. `*/30 6-21 * * *` or `*/15`) to capture destination arrival and shipper dispatch milestones in real-time.
- **Phase 1 (In-App Farm Inspection):**
  - Requires waking S7 devices and acquiring ADB device locks.
  - Must enforce a strict cooldown (5.5 - 6.0 hours) recorded in a state file (`order_phase1_sync_state.json`). Even when the cron ticks every 15-30 minutes, Phase 1 skips if within cooldown, protecting battery life, preventing device overheating, and respecting feeding shifts.

## 4. Silent Initialization Trap & Milestone Alert Discipline
- **The Trap:** Initializing an order's tracking state by silently saving `last_known_time` and doing `continue` swallows critical alerts if the order is already at the destination hub or out for delivery upon first discovery.
- **The Fix:** If the latest carrier event indicates destination arrival (`TTKT Đà Nẵng`, `bưu cục phát`, `Đống Đa`, `Thanh Khê`, `Hải Châu`) or shipper out-for-delivery, immediately emit the siren alert (`🚨 HÀNG VỀ ĐÀ NẴNG` / `🛵 SHIPPER ĐANG ĐI PHÁT`) even during state initialization.
- **Single Source Alerting:** Ensure only one module emits Telegram alerts for a carrier event to prevent duplicate notifications in the same cron tick.

## 5. WinRT OCR Kerning & Navigation Traps
- **Whitespace Kerning:** Fonts on high-DPI screens cause OCR to insert spaces into handles (e.g. `@khn h.vyyyy6`). Strip all whitespace before handle normalization: `_fold(text).replace(" ", "").replace("0", "o").lstrip("@")`.
- **Feed Tab False Positive:** The feed tab header contains "Đã follow" at `y < 200`. Never match profile stats above `y = 400`; profile counters ("Follower", "Following") strictly reside below `y = 400`.
- **Mall / Shop Direct Shortcut:** When on the TikTok Shop/Mall tab, tap the header shortcut "Đơn hàng" (`y < 500`) directly to enter the order center rather than swiping profile screens.
