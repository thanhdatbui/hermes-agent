# Navigation Target Profile Not Found Recovery (Case 105)

## 1. Bản chất sự cố
Trong flow nuôi tài khoản (`feed_swipe_smoke.py`, `calibrate_screens.py`), bước điều hướng vào tab Profile (`profile_preflight`) có thể dừng phiên với lỗi:
`manual-needed: navigation target profile not found in XML`

## 2. Nguyên nhân cốt lõi (Anti-Patterns)
1. **Bỏ sót Profile tab do badge hoặc resource-id**:
   - Tab Hồ sơ trên TikTok khi có thông báo sẽ mang `content-desc="Hồ sơ, 1 thông báo mới"` hoặc `"Hồ sơ mới"`, không khớp với tiền tố cứng `Hồ sơ,`.
   - Nhiều bản build TikTok đặt text rỗng trên node cha container mang resource-id chuẩn `:id/ofe` (`com.ss.android.ugc.trill:id/ofe` hoặc `*:id/ofe`).
2. **KEYCODE_BACK tùy tiện gây văng ra Launcher**:
   - Khi không tìm thấy target trong XML, nhánh back recovery gửi `input keyevent 4` mà không kiểm tra màn hình hiện tại.
   - Khi TikTok đang ở Trang chủ (Home Feed / For-You), nhấn BACK làm TikTok thoát ngay ra Samsung Launcher (`com.sec.android.app.launcher`).
3. **Che giấu lỗi gốc (Masking UIDumpError)**:
   - Lần capture UI retry gặp `UIDumpError` (như `ATX_SESSION_UNAVAILABLE` hoặc timeout), exception bị nuốt trong khối `except Exception:` và trả về chuỗi mặc định `"navigation target profile not found in XML"`.
4. **Preflight thiếu kiểm tra focus thực tế**:
   - `_navigate_profile_for_preflight` chỉ đọc chuỗi lỗi text từ `navigation.reason` mà không truy vấn `get_focused_activity(ctx)`. Khi máy đã bị văng về Launcher, hàm fail ngay lập tức thay vì kích hoạt relaunch.

## 3. Quy chuẩn xử lý & Invariants bắt buộc
1. **Nhận diện Profile linh hoạt trong `_find_navigation_element`**:
   - Hỗ trợ regex word boundary `rf"\b{re.escape(norm_term)}\b"` trong `_matches_marker`.
   - Bổ sung helper `_is_profile_resource_id` kiểm tra `:id/ofe`, `com.ss.android.ugc.trill:id/ofe`, `*:id/ofe`.
   - Tích hợp `_is_profile_resource_id` vào `extract_selected_markers` để nhận diện cờ `profile_selected`.
2. **Bảo toàn trung thực `UIDumpError`**:
   - Nếu lần capture ban đầu đã gặp `UIDumpError`, không chạy back recovery; giữ nguyên `status = exc.code` và `reason = str(exc)`.
   - Nếu lần retry dump gặp `UIDumpError`, gán `navigation_error = retry_exc` để không mask thành `"not-found"`.
3. **An toàn phím BACK tuyệt đối**:
   - **CẤM** gửi `input keyevent 4` nếu XML là Home/Feed (`for-you`, `following`, `friends`, `home`).
   - Kiểm tra `get_focused_activity`: nếu focus không xác định hoặc đã ở launcher / non-TikTok package, dừng gửi BACK ngay lập tức.
4. **Auto-Relaunch tại Preflight khi Launcher hoặc Target Not Found in XML**:
   - Trong `_navigate_profile_for_preflight`, khi navigation trả về fail (`not navigation.ok`):
     - Kiểm tra `is_launcher` (qua focus package thực tế hoặc reason chứa "launcher" / "focus lost").
     - Đồng thời kiểm tra `is_target_not_found` (`"not found in xml"` in `nav_reason_lower` hoặc `navigation.status == "not-found"`).
     - Nếu gặp `is_launcher` HOẶC `is_target_not_found`:
       - Ghi log retry với action `profile_preflight_relaunch_recovery`.
       - Relaunch TikTok qua `_relaunch_and_poll_tiktok_focus(ctx, after_launch_delay_seconds=POST_SWIPE_LAUNCHER_RECOVERY_WAIT_SECONDS)`.
       - **Pitfall về signature**: `_relaunch_and_poll_tiktok_focus` KHÔNG có tham số `timeout_s`. Tuyệt đối không truyền `timeout_s=...` vì sẽ gây `TypeError`.
       - **Đợi UI mount**: Bắt buộc chờ 2 giây (`time.sleep(2.0)`) sau khi relaunch thành công để TikTok kịp nạp lại layout và bottom bar.
       - Thử lại `tap_navigation_target(ctx, _profile_target(), artifact_prefix=artifact_prefix, log_prefix=artifact_prefix)` lần 2.
