# Case 105: Bẫy Phím BACK Trong Navigation Recovery, Mask Lỗi UIDumpError & Phục Hồi Launcher Focus (05/09/2026, Sự Cố Máy 52)

## 1. Hiện Tượng & Triệu Chứng Lỗi
- **Máy gặp lỗi:** Máy 52 | Serial: `ce0418243a6250430c` | Account: `vy.nguyen8730` (Row 1).
- **Quy trình:** Feed Session Smoke (`multi-machine-feed-session` trong `tiktok-luot nuoi acc`).
- **Triệu chứng báo cáo:** Dừng phiên tại `feed-session-smoke/profile_preflight` với stop_reason: `navigation target profile not found in XML` -> `manual-needed`.
- **Hiện trường thực tế khi inspect:** TikTok đang mở ở màn hình For You (Home Feed), nhưng sau khi runner chạy xong thì thiết bị bị rơi về Samsung Launcher (`com.sec.android.app.launcher.activities.LauncherActivity`).

---

## 2. Nguyên Nhân Cốt Lõi (4 Tầng Lỗi)

### Tầng 1: Bẫy Phím BACK Khi Ở Home Feed Làm Văng App Ra Launcher
- Trong `tap_navigation_target` (`python_runner/flows/calibrate_screens.py`), khi không tìm thấy target trong XML, nhánh back-recovery (attempt 1 & 2) gửi lệnh:
  `adb.shell(["input", "keyevent", "4"])` (KEYCODE_BACK).
- Khi TikTok đang ở màn hình Trang chủ (For-You / Home Feed), phím BACK là phím tắt thoát ứng dụng. Gửi BACK khiến TikTok bị đóng và thiết bị rơi về Launcher (`com.sec.android.app.launcher`).

### Tầng 2: Mask Lỗi UIDumpError Thành "Not Found In XML"
- Trong `tap_navigation_target`, khi `capture_required_ui` ném ra `UIDumpError` (ví dụ `ATX_SESSION_UNAVAILABLE` hoặc adb transport timeout do kết nối mạng/socket gián đoạn):
  ```python
  except UIDumpError as exc:
      navigation_error = exc
  ```
  Sau đó ở nhánh `if point is None:`, nếu không xử lý cẩn thận, mã lỗi gốc bị che khuất và reason bị gán cứng thành:
  `navigation target {target.name} not found in XML`.
- Điều này đánh lừa các tầng giám sát phía trên, khiến hệ thống tưởng rằng UI đọc thành công nhưng thiếu node Profile, trong khi thực tế là việc đọc XML gặp sự cố hoặc app đã bị đóng.

### Tầng 3: Selector Tab Profile Quá Hẹp (Bỏ Sót Badge Thông Báo & Resource-Id)
- Trong `_find_navigation_element` (`calibrate_screens.py`), hàm chỉ lọc candidates bằng:
  `_element_matches(element, target.terms)` (so khớp chuỗi `Hồ sơ`, `Profile` qua `_matches_marker`).
- Nếu tab Profile trên TikTok có badge thông báo đỏ hoặc chấm đỏ, `content-desc` có thể trở thành `"Hồ sơ, có thông báo mới"` hoặc kèm số thông báo. Nếu logic so khớp không có word boundary hoặc regex linh hoạt, node sẽ bị bỏ qua.
- Hơn nữa, container của tab Profile có resource-id chuẩn `:id/ofe` (`com.ss.android.ugc.trill:id/ofe`), nhưng `_find_navigation_element` trước đây không kiểm tra resource-id mà chỉ dựa vào text.

### Tầng 4: Thiếu Cơ Chế Tự Động Relaunch Khi Mất Focus Trong `_navigate_profile_for_preflight`
- Tại `flows/feed_swipe_smoke.py::`_navigate_profile_for_preflight`, hàm chỉ kiểm tra launcher nếu `nav_reason_lower` chứa `"launcher"`.
- Vì lý do lỗi bị gán cứng là `"navigation target profile not found in XML"`, cờ `is_launcher` bị `False`. Runner không kích hoạt `_relaunch_and_poll_tiktok_focus` mà vội vã kết luận `manual-needed`, khiến máy bị dừng oan dù TikTok vẫn hoàn toàn bình thường.

---

## 3. Quy Tắc Khắc Phục Chuẩn (Standard Fix Pattern)

1. **Bảo toàn Exception Gốc (No Masking):**
   - Giữ nguyên `UIDumpError` (`exc.code` và `str(exc)`) làm `navigation_reason`, không bao giờ ghi đè thành `"navigation target X not found in XML"` khi bản thân thao tác dump UI thất bại.

2. **An Toàn Phím BACK Trong Navigation Recovery:**
   - Trước khi gửi `KEYCODE_BACK`, bắt buộc kiểm tra trạng thái màn hình hiện tại:
     * Nếu thiết bị đang ở Launcher hoặc không phải TikTok package -> CẤM gửi phím BACK (tránh làm kẹt sâu hơn ở Launcher).
     * Nếu màn hình đã xác nhận là Home Feed / For You (đã có bottom bar hoặc top tabs) -> KHÔNG gửi phím BACK để tìm tab Profile, vì tab Profile nằm ngay trên bottom bar của Home. Thay vào đó thử re-capture hoặc cuộn/giải phóng overlay.

3. **Mở Rộng Nhận Diện Tab Profile:**
   - Trong `_find_navigation_element`, hỗ trợ tìm theo `resource_id` (`:id/ofe` hoặc kết thúc bằng `/ofe`) ở dải tọa độ đáy ($y \ge 1400$, $x \ge 700$).
   - Dùng word boundary hoặc accent-normalized matching cho `Hồ sơ` / `Profile` khi text/content-desc có đính kèm số badge hoặc dấu thông báo.

4. **Active Focus Check Trong `_navigate_profile_for_preflight`:**
   - Khi `navigation.ok` là `False`, luôn gọi `get_focused_activity(ctx)` để kiểm tra package thực tế. Nếu phát hiện package là Launcher hoặc không thuộc TikTok packages, tự động gọi `_relaunch_and_poll_tiktok_focus` để đưa TikTok trở lại foreground, sau đó thử lại `tap_navigation_target` 1 lần trước khi fail.
