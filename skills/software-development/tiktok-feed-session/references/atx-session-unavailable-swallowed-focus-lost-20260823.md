# ATX_SESSION_UNAVAILABLE Swallowed → Phantom "TikTok focus lost" (2026-08-23)

## Triệu chứng
- Alert: `🚨 [MÁY XX] DỪNG PHIÊN` / `Lý do: TikTok focus lost`
- Ảnh hiện trường: TikTok đang hiển thị feed bình thường (không phải launcher)
- Log: `tap_profile/verify_tiktok_focus → failed | pkg=com.android.systemui`
- Khoảng trống ~2 phút trong log trước khi lỗi xảy ra

## Chuỗi sự kiện (log machine_10, 2026-08-23 row-1-100039)
```
03:22:17  baseline_gemphonefarm_blind_popup/close_all_desc  → miss
03:23:34  baseline_gemphonefarm_blind_popup_close_all_desc_probe_2/dump_current_ui
          → result=skipped | error=ATX_SESSION_UNAVAILABLE: ATX session UI capture failed after retry and reset
03:24:22  tap_profile/verify_tiktok_focus → FAILED | safety=TikTok focus lost
03:26:25  profile_preflight_navigation_blocker → ATX_SESSION_UNAVAILABLE, pkg=com.android.systemui
03:26:26  profile_preflight → manual-needed, cleanup_close_all → skipped (preserve_blocker_screen)
```

## Root cause
Trong `python_runner/flows/feed_swipe_smoke.py`, hàm `dump_current_ui` bắt `UIDumpError` và kiểm tra `terminal_recovery`:

```python
terminal_recovery = (
    exc.code == "CAPTURE_RECOVERY_ATTEMPT_BUDGET_EXHAUSTED"
    or any(...)  # FINAL_BLOCKED check
)
```

`ATX_SESSION_UNAVAILABLE` **không nằm** trong điều kiện → `terminal_recovery = False` → log `result="skipped"` rồi **`return None`**. Flow tiếp tục sang `tap_profile` trong khi ATX đã chết và OS đang giữ `com.android.systemui` ở foreground.

## Fix (commit 52a8bc9)
Thêm `ATX_SESSION_UNAVAILABLE` vào điều kiện terminal:

```python
terminal_recovery = (
    exc.code == "CAPTURE_RECOVERY_ATTEMPT_BUDGET_EXHAUSTED"
    or exc.code == "ATX_SESSION_UNAVAILABLE"   # ← dòng thêm
    or any(
        isinstance(attempt, dict)
        and str(attempt.get("recovery_state") or "") == "FINAL_BLOCKED"
        for attempt in (exc.attempts or ())
    )
)
```

File: `python_runner/flows/feed_swipe_smoke.py` dòng ~1276

## Phân biệt với UIAutomator focus-loss
Lỗi này **không phải** UIAutomator chiếm foreground (reference: `uiautomator-monkey-focus-loss-feed-stuck-20260823.md`).
- Pattern UIAutomator: ảnh hiện trường là `com.github.uiautomator.MainActivity`
- Pattern ATX swallowed: ảnh là TikTok feed bình thường, `pkg=com.android.systemui` chỉ xuất hiện tại bước verify_tiktok_focus SAU khoảng trống ~2 phút trong log

## Cách chẩn đoán
1. Tìm khoảng trống thời gian lớn (>1 phút) trong log máy bị dừng
2. Grep: `ATX_SESSION_UNAVAILABLE` + `result=skipped` ngay trước khoảng trống
3. Nếu có → đây là pattern này, không phải UIAutomator/launcher focus loss

## Test evidence
- 347 passed, 2 pre-existing failed, 0 regression
- `test_flow_stops_on_focus_loss_before_navigation` — pre-existing Mock issue, không liên quan
