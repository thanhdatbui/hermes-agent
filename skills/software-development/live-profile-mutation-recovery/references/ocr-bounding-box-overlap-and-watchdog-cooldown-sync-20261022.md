# WinRT OCR Bounding Box Vertical Overlap & Watchdog Cooldown State Persistence

## 1. WinRT OCR Bounding Box Vertical Overlap Trap

### 1.1 Root-Cause Analysis on Samsung S7 (1080x1920)
On Samsung S7 profile screens, the Display Name (Biệt danh, e.g. "Xuan Toän") and the Username handle (e.g. "@toansuong04") sit directly on top of each other with minimal padding.
When processed through WinRT OCR (`Windows.Media.Ocr.OcrEngine`), character ascenders/descenders and text-line grouping heuristics cause the bounding boxes to overlap along the vertical Y-axis:
```text
Display Name:  x1=310, y1=539, x2=554, y2=607  ("Xuan Toän")
Username:      x1=336, y1=588, x2=638, y2=667  ("@toansuong04")
                      ^^^^^^^^         ^^^^^^^
                      y1=588           y2=607 (Overlap = 19px!)
```

### 1.2 The Fatal Flaw in `b2[3] <= user_box[1]`
A naive geometric check for "box B2 is above box B1" often requires the bottom of B2 to be strictly above or equal to the top of B1:
```python
# ANTI-PATTERN: Fails whenever OCR boxes overlap vertically!
if b2[3] <= user_box[1] + 5 and user_box[1] - b2[3] < 120:
    ...
```
Because `607 <= 588 + 5` evaluates to `False`, the candidate box is rejected. The extractor returns `name = None`, falsely aborting an otherwise 100% successful rename with:
`Abort("da Luu nhung Ten tren Ho so (OCR) = None, khong phai 'Xuân Toàn'")` (exit code 2).

### 1.3 The Robust Top-to-Top Invariant
Always compare top-edge coordinates (`y1`) with a vertical distance window, while requiring horizontal overlap:
```python
# CORRECT & ROBUST:
if b2[1] < user_box[1] and user_box[1] - b2[1] < 120 and b2[0] < user_box[2]:
    ...
```
In the overlap case above:
- `b2[1] < user_box[1]` -> `539 < 588` (True)
- `user_box[1] - b2[1] = 49 < 120` (True)
- `b2[0] < user_box[2]` -> `310 < 638` (True)
The display name is recognized cleanly without false-negative aborts.

---

## 2. Watchdog Cooldown State Persistence (`rename_natural_state.json`)

### 2.1 The Silent Re-queue Storm
When a canonical runner executes outside the watchdog (e.g. manual Canary run or hotfix intervention):
1. The profile is successfully renamed on TikTok.
2. TikTok backend starts its strict 7-day cooldown clock (`TikTok gioi han 7 ngay`).
3. If the script does not record this event into `rename_natural_state.json`, the watchdog's candidate scanner (`load_candidates()`) still considers the account eligible.
4. On every subsequent 15-minute cron cycle, the watchdog re-dispatches the account. The runner navigates into `NAME_EDIT`, encounters TikTok's 7-day modal, and aborts with `exit_2`, generating false alert spam.

### 2.2 Watchdog Cooldown Invariant
- **Runner State Reporting:** When encountering the in-app 7-day cooldown notice (`tiep tuc thay doi`, `sau ngay`), the runner records `"reason": "TikTok gioi han 7 ngay: ..."` in `REPORT_JSON`.
- **Watchdog State Sync:** In `tiktok_rename_rolling_watchdog.py`, the collector parses `jdata.get("reason")`. If `TikTok gioi han 7 ngay` is detected:
  - Mark `is_already = "COOLDOWN_7D"`.
  - Suppress the `_fail()` alarm.
  - Commit `state[u] = {"machine": m, "new_name": n, "renamed_at": now(), "verified": True, "cooldown": True}` to `rename_natural_state.json`.
  - The account is automatically skipped for `COOLDOWN_DAYS = 7`, eliminating repetitive alert fatigue.

---

## 3. Night Shift 2FA Task Priority (`tiktok-add-bao-mat-f2a`)
- From 22:30 onwards, farm devices are scheduled for batch 2FA binding (`batch-live-2fa-reservation`).
- Rename runners must respect `acquire_device_lock`: when a lock is held by `tiktok-add-bao-mat-f2a`, emit `SAFE_SKIP` and exit 0 cleanly without attempting to force-preempt or kill the active security process.
