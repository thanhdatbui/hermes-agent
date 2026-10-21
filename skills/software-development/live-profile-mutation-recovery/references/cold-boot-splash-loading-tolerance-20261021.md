# Cold-Boot Splash / Loading Screen Tolerance Invariant (2026-10-21)

## Problem & Root Cause

During rolling TikTok profile mutations / automation on farm devices (e.g. M31, M4):
- Multiple devices failed with `exit_2`: `ABORT: ket o trang thai UNKNOWN 5 lan lien tiep`.
- Trace log analysis (`m31_nana34874_rename_confirmed.json`, `m4_votam5319_rename_confirmed.json`) showed:
  - Step s01 (09:45:45): OCR `['TikTok']` (`SplashActivity`)
  - Step s02 (09:45:51): OCR `['TikTok']`
  - Step s03 (09:45:57): OCR `['TikTok']`
  - Step s04 (09:46:03): OCR `['TikTok']`
  - Step s05 (09:46:09): OCR `['TikTok']` (or blank) -> Aborted due to `same > MAX_SAME_STATE` (where `MAX_SAME_STATE = 4`).
  - Step s06 / final verification screenshot (09:46:14): Immediately after abort, the device had entered `FEED` cleanly (`Trang chủ`, `Cửa hàng`, `Hộp thư`, `Hồ sơ`).

## The Core Invariant

1. **Slow Network / Proxy Cold-Boot Latency:** When launching TikTok from cold state (`am force-stop` followed by launcher monkey), devices operating on 4G cellular proxies take 25–35 seconds to pass network handshake, token refresh, and splash screen ads.
2. **Distinguish Splash vs Stuck UNKNOWN:**
   - A stuck UNKNOWN on an unexpected popup or frozen app usually has error dialogs, system UI strings, or nhiều dòng text.
   - A splash/loading screen has minimal text (`len(lines) <= 3 and not errors_in(lines)`), typically just the word `TikTok` or an empty black/white splash surface.
3. **Tolerance Expansion:**
   - When `state == "UNKNOWN"` and `len(lines) <= 3 and not errors_in(lines)`, grant an extended tolerance window (up to 8 steps / ~35–40s) before tripping consecutive same-state circuit breakers.
   - Do NOT send `BACK` keyevent during cold splash loading, as pressing `BACK` prematurely kills or backgrounds the launching activity.
