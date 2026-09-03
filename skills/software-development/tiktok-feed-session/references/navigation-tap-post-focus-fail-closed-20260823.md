# Navigation Tap Post-Focus Fail-Closed Contract & Anti-Relaunch Pattern (2026-08-23)

## Bối cảnh sự cố
- Màn hình alert máy 44 báo lỗi `profile verification navigation failed: TikTok focus lost`, ảnh hiện trường hiển thị màn hình Recent Apps (`com.android.systemui`).
- Nguyên nhân: Hàm `tap_navigation_target()` chỉ kiểm tra TikTok focus trước khi tap. Sau khi tap nút navigation (ví dụ tab Hồ sơ/Profile), nếu hệ điều hành hoặc máy rơi vào Recent Apps / SystemUI, hàm vẫn trả về `ok=True`.
- Hậu quả: Caller (`_navigate_profile_for_preflight` / `read_profile_identity`) tiếp tục chạy, đọc XML cũ hoặc màn hình SystemUI và quăng lỗi profile identity / focus lost muộn, làm sai lệch chẩn đoán.

## Nguyên tắc: Fail-Closed tại Low-Level Navigation Tap
Sau khi thực hiện `input tap`, `tap_navigation_target()` bắt buộc kiểm tra lại foreground activity:
```python
post_focus = get_focused_activity(ctx)
post_package = str(post_focus.get("package") or "")
if post_package != expected_package:
    # Log verify_tiktok_focus_after_navigation và trả về NavigationResult(False, "fail", ...)
```

## Tại sao CẤM tự động Relaunch/Force-Stop bên trong `tap_navigation_target()`?
Khi gặp câu hỏi "Tại sao khi văng ra ngoài không tự mở lại app ngay lúc tap?":
1. **Sai phân tầng trách nhiệm (Layering):**
   - `tap_navigation_target` là hàm tiện ích cấp thấp phục vụ nhiều flow khác nhau (baseline calibration, preflight, verify profile, switch tabs, home).
   - Tự ý force-stop/relaunch ở hàm tap sẽ bypass các cờ an toàn (`allow_prepare_tiktok`, `allow_network_force_stop_recovery`) và phá vỡ cấu trúc recovery của caller.
2. **Nguy cơ lặp vòng relaunch vô tận:**
   - Quy tắc farm: tối đa 1 lần force-stop/relaunch trong ladder.
   - Nếu mỗi cú tap trượt đều tự relaunch, luồng điều hướng sẽ liên tục reset app mà không có giới hạn chặt chẽ.
3. **Bảo toàn chẩn đoán chính xác:**
   - Việc fail-closed ngay lập tức cho phép tầng caller nhận đúng lỗi `TikTok focus lost after navigation tap`, từ đó caller quyết định kích hoạt recovery có kiểm soát hoặc dừng fail-closed, thay vì đọc nhầm XML của app khác.

## Bổ sung Relaunch ở đâu nếu cần?
Nếu nghiệp vụ yêu cầu phục hồi sau khi tap Profile bị văng:
- Đặt handler tại tầng **caller cấp cao** (ví dụ `_navigate_profile_for_preflight`), tương tự như `_recover_post_swipe_launcher_focus` (có log `launcher_focus_recovery`, state machine `DETECTED -> RECOVERING -> VERIFIED_SUCCESS | FINAL_BLOCKED`, recapture và kiểm tra feed/profile).
- Tuyệt đối không nhét logic relaunch vào hàm tap nguyên tử `tap_navigation_target()`.
