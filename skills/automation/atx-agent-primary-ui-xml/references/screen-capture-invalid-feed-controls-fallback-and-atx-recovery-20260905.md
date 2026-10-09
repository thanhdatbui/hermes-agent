# Fallback Feed Controls & Phục Hồi ATX Session Khi 'Screen Capture Invalid; Feed Not Confirmed' (Case 114, 2026-09-05, Máy 19)

## 1. Hiện tượng và bối cảnh (Context & Symptoms)
- **Thiết bị**: Máy 19 (Samsung Galaxy S7, Android 7, serial `ce0216027451853102`).
- **Quy trình**: Nuôi Acc / Lướt Feed (`tiktok-luot nuoi acc`).
- **Triệu chứng dừng phiên**:
  ```text
  [FARM ALERT: MÁY 19] DỪNG PHIÊN
  • Quy trình: Nuôi Acc / Lướt Feed (tiktok-luot nuoi acc)
  • Máy: 19 | Serial: ce0216027451853102 | Nick: haihuong980
  • Triệu chứng: screen capture invalid; feed not confirmed
  • Hiện trường: ĐANG MỞ
  ```
- **Hiện trường máy thật**: TikTok đang mở bình thường ở foreground (`com.ss.android.ugc.trill/com.ss.android.ugc.aweme.splash.SplashActivity`), video và các tab Trang chủ / Đề xuất (For You) hiển thị đầy đủ trên màn hình.

---

## 2. Nguyên nhân cốt lõi (Root Cause)

### Lỗ hổng 1: Thiếu mã lỗi `ATX_SESSION_UNAVAILABLE` trong fallback nhận diện feed controls từ ảnh
- Trong `python_runner/flows/calibrate_screens.py` (hàm `capture_calibration_attempt`):
  ```python
  if (
      screenshot_path
      and not details.get("detected_screen")
      and details.get("focused_package") == str(ctx.config.get("tiktok_package", "com.ss.android.ugc.trill"))
      and xml_error_code in {"uiautomator_idle_state_error", "ui_dump_file_missing", "ui_dump_command_failed", "uiautomator_null_root_node"}
  ):
      feed_controls = detect_feed_controls(screenshot_path.read_bytes())
  ```
- Khi farm chuyển sang 100% ATX session UI XML (`core/ui_capture.py`), nếu daemon/stub ATX gặp sự cố hoặc timeout trên máy cấu hình yếu, exception văng ra là `UIDumpError("ATX_SESSION_UNAVAILABLE")` hoặc `"ui_dump_failed"`.
- Do set trên chỉ kiểm tra 4 mã lỗi uiautomator cũ, nhánh fallback sang `detect_feed_controls(screenshot_path.read_bytes())` bị bỏ qua hoàn toàn. Dù ảnh chụp màn hình chứa đầy đủ các icon/nút feed controls, hàm vẫn trả về `details` với `detected_screen = None` và `xml_error_code = "ATX_SESSION_UNAVAILABLE"`.

### Lỗ hổng 2: Thiếu bước auto-recover ATX agent trong `_capture_step`
- Trong `python_runner/flows/feed_swipe_smoke.py` (`_capture_step`):
  - Khi lần capture đầu tiên bị lỗi (`_capture_retry_needed` trả về `True`), flow nhảy thẳng vào force stop app (`_capture_invalid_force_stop_recovery`) hoặc dừng phiên.
  - Khi TikTok **vẫn đang ở foreground** (`cur_pkg in tiktok_packages`) nhưng ATX session bị nghẽn socket hoặc stub rớt, việc force-stop app hoặc fail-closed là quá sớm và gây gián đoạn phiên nuôi acc không đáng có.

---

## 3. Giải pháp chuẩn hóa (Standard Fix Pattern)

### 3.1. Bổ sung `ATX_SESSION_UNAVAILABLE` và `ui_dump_failed` vào fallback feed controls (`calibrate_screens.py`)
```python
and (
    xml_error_code in {
        "uiautomator_idle_state_error",
        "ui_dump_file_missing",
        "ui_dump_command_failed",
        "uiautomator_null_root_node",
        "ATX_SESSION_UNAVAILABLE",
        "atx_session_unavailable",
        "ui_dump_failed",
    }
    or xml_error_code.lower() in {"atx_session_unavailable", "ui_dump_failed"}
)
```

### 3.2. Auto-recover ATX agent trong `_capture_step` (`feed_swipe_smoke.py`)
Ngay trước khi gọi `_capture_invalid_force_stop_recovery`:
```python
if _capture_retry_needed(attempt, require_feed=require_feed, expected=expected):
    current_focus = get_focused_activity(ctx)
    cur_pkg = str(current_focus.get("package") or "")
    tiktok_packages = {
        str(ctx.config.get("tiktok_package", "com.ss.android.ugc.trill")),
        "com.ss.android.ugc.trill",
        "com.zhiliaoapp.musically",
        "com.ss.android.ugc.aweme",
    }
    if cur_pkg in tiktok_packages and (
        _has_invalid_screenshot(attempt)
        or _xml_error(attempt) in {"ATX_SESSION_UNAVAILABLE", "atx_session_unavailable"}
        or not _is_feed_confirmed(attempt, expected=expected)
    ):
        try:
            from automation_core.persistent_ui import reset_atx_agent
            reset_atx_agent(ctx.adb, timeout=15)
            time.sleep(1.0)
            recheck_attempt = capture_calibration_attempt(
                ctx,
                step,
                len(attempts) + 1,
                focus=current_focus,
                artifact_prefix=artifact_prefix,
                log_prefix=artifact_prefix,
            )
            _annotate_screenshot_size(recheck_attempt)
            attempts.append(recheck_attempt)
            if _is_feed_confirmed(recheck_attempt, expected=expected):
                attempt = recheck_attempt
        except Exception as reset_exc:
            ctx.logger.log(
                device_id=ctx.device_id,
                account=ctx.account,
                step=f"{artifact_prefix}/{step}",
                action="atx_recovery_attempt",
                result="failed",
                error=str(reset_exc),
            )
```

---

## 4. Quy tắc nghiệm thu (Verification Checklist)
1. **Unit test**: Test `test_calibrate_screens.py` và `test_navigation_focus_recovery.py` phải pass 100%.
2. **Canary test trên thiết bị**: Chạy `run-feed-session.ps1` với `-RecoveryTestSwipes 2 -Run` đạt `final_status: success`.
3. **Banner báo cáo**: Tạo ảnh `m<N>_verified_banner.png` có banner đỏ `[MAY N] - <time> - VERIFIED` gửi kèm tin nhắn recovery trọn gói `<= 1024` ký tự.
