# Phục Hồi Lỗi "Screen Capture Invalid; Feed Not Confirmed" & Fallback Image Feed Controls (Case 112, 2026-09-05, Máy 19)

## 1. Hiện Trường & Triệu Chứng
- **Alert**: `[FARM ALERT: MÁY 19] DỪNG PHIÊN`
- **Quy trình**: Nuôi Acc / Lướt Feed (`tiktok-luot nuoi acc`)
- **Thiết bị**: Máy 19 (ce0216027451853102), Nick: `haihuong980`
- **Triệu chứng**: `screen capture invalid; feed not confirmed` (`SCREEN_CAPTURE_INVALID_REASON`).
- **Hiện trường thực tế**: TikTok vẫn đang mở ở foreground (`com.ss.android.ugc.trill/com.ss.android.ugc.aweme.splash.SplashActivity`), hiển thị bài viết dạng text post của `decorvibes_` trên tab "Đề xuất" (For You feed). `atx-agent` đang LISTEN 7912, nhưng shell `uiautomator dump` bị `Killed` (EXIT=137).

## 2. Root Cause Analysis
Có 2 điểm nghẽn logic cốt lõi dẫn đến việc dừng phiên oan:

1. **Thiếu `ATX_SESSION_UNAVAILABLE` trong fallback `detect_feed_controls` (`calibrate_screens.py`)**:
   - Tại dòng 834 của `calibrate_screens.py`:
     ```python
     if (
         screenshot_path
         and not details.get("detected_screen")
         and details.get("focused_package") == str(ctx.config.get("tiktok_package", "com.ss.android.ugc.trill"))
         and xml_error_code in {"uiautomator_idle_state_error", "ui_dump_file_missing", "ui_dump_command_failed", "uiautomator_null_root_node"}
     ):
     ```
   - Khi uiautomator stub hoặc ATX session dump bị rớt / timeout trên dòng máy Samsung S7 (Android 7), exception trả về là `UIDumpError("ATX_SESSION_UNAVAILABLE")` với `xml_error_code = "ATX_SESSION_UNAVAILABLE"`.
   - Vì danh sách lỗi trên không chứa `"ATX_SESSION_UNAVAILABLE"`, flow hoàn toàn bỏ qua cơ chế cứu cánh `detect_feed_controls(screenshot_path.read_bytes())`, dù ảnh chụp screenshot hoàn toàn bình thường và rõ ràng là màn hình TikTok Feed. Do đó, `details["detected_screen"]` bị bỏ trống (`None`).

2. **Thiếu Bước Phục Hồi ATX Agent Trong `_capture_step` (`feed_swipe_smoke.py`)**:
   - Trong `_capture_step()`, khi capture attempt bị đánh dấu `_capture_retry_needed` do capture invalid hoặc feed not confirmed:
   - Nếu TikTok vẫn đang ở foreground (`focus_package in KNOWN_TIKTOK_PACKAGES`), hệ thống nhảy thẳng sang force-stop app (`_capture_invalid_force_stop_recovery`) hoặc fail-closed với `SCREEN_CAPTURE_INVALID_REASON` mà thiếu bước cứu ATX agent tại chỗ.
   - Khi `atx-agent` hoặc stub socket bị lag tạm thời, việc gọi `reset_atx_agent(ctx.adb, timeout=15)` và recapture ngay lập tức có thể khôi phục 100% kết nối UI XML mà không làm gián đoạn phiên lướt.

3. **Pitfall Tooling `inspect_machine.py` Thiếu Fallback Đường Dẫn ADB**:
   - `D:/Taadaa/tools/inspect_machine.py` chỉ gọi bare command `adb devices`. Nếu terminal/subagent không có `adb` trong `PATH`, lệnh quăng lỗi `FileNotFoundError: [WinError 2] The system cannot find the file specified`.
   - Phải hỗ trợ fallback tìm `C:\Program Files (x86)\xiaowei\tools\adb.exe`.

## 3. Quy Chuẩn Khắc Phục (Code Fix)
1. **Mở rộng danh sách XML degraded errors trong `calibrate_screens.py`**:
   ```python
   and xml_error_code in {
       "uiautomator_idle_state_error",
       "ui_dump_file_missing",
       "ui_dump_command_failed",
       "uiautomator_null_root_node",
       "ATX_SESSION_UNAVAILABLE",
       "atx_session_unavailable",
       "ui_dump_failed",
   }
   ```
2. **Tự động phục hồi ATX trong `_capture_step` (`feed_swipe_smoke.py`)**:
   - Trước khi force-stop hoặc trả về failed step, kiểm tra nếu `focus.get("package") in KNOWN_TIKTOK_PACKAGES` và attempt bị lỗi do ATX / capture invalid:
   - Gọi `reset_atx_agent(ctx.adb, timeout=15)` an toàn.
   - Thử recapture `capture_calibration_attempt` 1 lần với bounded deadline.
   - Nếu recapture xác nhận được feed (`_is_feed_confirmed`), cập nhật `attempt` và tiếp tục phiên lướt bình thường.
