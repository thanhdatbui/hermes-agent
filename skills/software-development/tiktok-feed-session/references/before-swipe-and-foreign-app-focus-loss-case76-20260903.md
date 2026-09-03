# Case 76: Before-Swipe & Foreign App Focus Loss Recovery & Anti-False-Positive Login (2026-09-03)

## 1. Hiện tượng & Bối cảnh (Sự cố Máy 51)
- **Cảnh báo farm:** `🚨 [MÁY 51] DỪNG PHIÊN: TikTok focus lost` trong `multi-machine-feed-session` với tài khoản `jomegbym8n8`.
- **Hiện trường thiết bị:**
  - TikTok bị văng ngầm ra ngoài màn hình chính (Launcher `com.sec.android.app.launcher`) hoặc bị ứng dụng hệ thống/bên ngoài chiếm foreground (ví dụ Samsung Pay `com.samsung.android.spay`).
  - Tại nhịp khởi động ban đầu (`baseline`) hoặc ngay trước lượt vuốt đầu tiên (`before_swipe`), runner kiểm tra focus và trả về `status: failed`, `reason: TikTok focus lost`.

## 2. Nguyên nhân cốt lõi (Anti-Patterns)
1. **Thiếu cơ chế Relaunch Recovery tại `before_swipe`:**
   - Trong `_feed_session_flow`, khi `before_swipe` trả về `failed` do mất focus, runner không kích hoạt `_recover_post_swipe_launcher_focus` / `_relaunch_and_poll_tiktok_focus` mà nhảy thẳng vào `_swipe_recovery_on_stuck`.
   - Lệnh vuốt mù ngoài Launcher hoàn toàn vô nghĩa và cạn kiệt số lần retry, dẫn đến dừng phiên giữ hiện trường.
2. **Nhận diện Focus Loss hạn hẹp (`_is_launcher_focus_loss`):**
   - Trước đây chỉ kiểm tra danh sách cứng `LAUNCHER_PACKAGES` (Samsung Launcher, NexusLauncher, Launcher3, SystemUI).
   - Khi các app hệ thống/bên ngoài như Samsung Pay (`com.samsung.android.spay`) chiếm focus, `_is_launcher_focus_loss` trả về `False`, khiến hệ thống không kích hoạt phục hồi.
3. **False-Positive Login Screen trên Foreign Apps:**
   - Khi app ngoài (`com.samsung.android.spay`) hiển thị UI có text "Đăng nhập / Tài khoản", bộ bóc tách XML (`classifier.py` và `benign_popup.py`) quét text và phân loại nhầm thành màn hình nhạy cảm `manual-needed:login` của TikTok, gây dừng toàn bộ phiên nuôi.

## 3. Giải pháp chuẩn hóa (Case Fix)
1. **Mở rộng nhận diện Focus Loss:**
   - Trong `_is_launcher_focus_loss`, bất kỳ `focus_package` nào không thuộc `tiktok_pkgs` (ngoại trừ hộp thoại cấp quyền Android `is_packageinstaller_dialog`) đều được coi là mất focus.
2. **Bọc Relaunch Recovery đồng bộ:**
   - Tại `_capture_before_swipe_with_startup_retry`: Khi phát hiện `_is_launcher_focus_loss(ctx, row)`, tự động gọi `_relaunch_and_poll_tiktok_focus` nạp lại TikTok và capture lại `before_swipe_launcher_recovery_recapture`.
   - Tại `_feed_session_flow` (nhịp `before_swipe`): Khi `before` bị lỗi, nếu là focus loss thì kích hoạt `_recover_post_swipe_launcher_focus` và cập nhật lại partial result trước khi fallback `_swipe_recovery_on_stuck`.
   - Tại `_capture_baseline_with_startup_retry`: Tương tự, nếu phát hiện focus loss thì relaunch và recapture `baseline_launcher_recovery_recapture`.
3. **Chống False-Positive Login:**
   - Trong `classifier.py` (`classify_tiktok_screen`) và `benign_popup.py` (`has_sensitive_marker`): Khi `focused_package` không thuộc `tiktok_pkgs` và không phải `packageinstaller`, cấm phân loại thành `manual-needed:login` / marker nhạy cảm của TikTok.

## 4. Quy tắc vận hành Agent (Coordinator-Worker Delegation)
- **`delegate_task` là bất đồng bộ (background):** Sau khi dispatch task cho worker, session chính báo ngay cho người dùng và sẵn sàng nhận lệnh mới.
- **CẤM TUYỆT ĐỐI dùng vòng lặp `sleep` trong terminal** để chờ subagent xong vì sẽ gây nghẽn phiên và tạo cảm giác treo/im lặng cho người dùng.
