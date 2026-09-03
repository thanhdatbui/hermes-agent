# Foreign App Focus Loss, Before-Swipe Recovery & Non-Blocking Subagent Workflow (Case 76, 2026-09-02)

## 1. Hiện tượng & Triệu chứng
- **Alert:** `🚨 [MÁY N] DỪNG PHIÊN • Script: multi-machine-feed-session • Lý do: TikTok focus lost • Trạng thái: GIỮ HIỆN TRƯỜNG`.
- **Hiện trường:** Thiết bị đang ở Samsung Pay (`com.samsung.android.spay`), Samsung Launcher (`com.sec.android.app.launcher`), hoặc app bên ngoài chiếm foreground.
- **Log Runner:** Trả về `TikTok focus lost` hoặc bị phân loại nhầm thành `manual-needed:login` (False-Positive Login).

---

## 2. Nguyên nhân Gốc rễ (Root Cause)

1. **Bỏ lọt Package ngoài (`_is_launcher_focus_loss` hẹp):**
   - Trước đây `_is_launcher_focus_loss` chỉ đối soát danh sách cứng `LAUNCHER_PACKAGES` (Samsung Launcher, NexusLauncher, Launcher3, SystemUI).
   - Khi app hệ thống như Samsung Pay (`com.samsung.android.spay`), Google Play hay app bên thứ ba bật lên, `_is_launcher_focus_loss` trả về `False`, khiến runner không nhận diện được đây là lỗi mất focus.

2. **False-Positive Login trên App ngoài:**
   - Bộ phân loại màn hình XML (`classify_tiktok_screen`, `has_sensitive_marker`) quét text của app ngoài. Nếu app ngoài có chữ "Đăng nhập / Sign in / Account", classifier đánh dấu nhầm thành `manual-needed:login` của TikTok và dừng khẩn cấp.

3. **Thiếu Recovery tại Phase `baseline` & `before_swipe`:**
   - Trong `feed_swipe_smoke.py`, cơ chế `_recover_post_swipe_launcher_focus` trước đây chỉ được bọc kỹ ở vòng lặp vuốt `after_swipe`.
   - Tại `baseline` và `before_swipe`, khi mất focus, script nhảy thẳng vào `_swipe_recovery_on_stuck` (vuốt ADB mù trên launcher/app ngoài) -> cạn kiệt retry -> fail phiên.

---

## 3. Quy chuẩn Sửa Code (`python_runner` & `automation-core`)

### A. Mở rộng `_is_launcher_focus_loss` (Fail-Closed cho Foreign App)
- Bất kỳ foreground package nào **không thuộc `tiktok_pkgs`** (và không phải hộp thoại cấp quyền `is_packageinstaller_dialog`) BẮT BUỘC được tính là mất focus (`return True`).

### B. Chống False-Positive Login
- Trong `core/classifier.py` / `core/benign_popup.py`: Nếu `focused_package` không thuộc `tiktok_pkgs` (và không phải packageinstaller), **CẤM** gán nhãn `manual-needed:login` hay các sensitive marker của TikTok. Phải trả về `screen="unknown", manual_needed=False` để nhường quyền cho bộ kiểm tra focus loss.

### C. Bọc Recovery đồng bộ tại Mọi Nhịp
1. **Tại `_capture_baseline_with_startup_retry`:**
   - Nếu `_is_launcher_focus_loss(ctx, row)` -> gọi `_relaunch_and_poll_tiktok_focus` (delay 10s) -> recapture `baseline_launcher_recovery_recapture`.
2. **Tại `_capture_before_swipe_with_startup_retry` & `_feed_session_flow` (`before_swipe`):**
   - Nếu `_is_launcher_focus_loss(ctx, before)` -> gọi `_recover_post_swipe_launcher_focus` -> cập nhật `results[-1]` và lưu partial result.
3. **Tại `after_swipe` & `verify_profile`:**
   - Duy trì cơ chế 2 tầng: Tầng 1 Fast Relaunch (10s) + Tầng 2 Guarded Reboot (1 lần/phiên).

---

## 4. Quy tắc Vận hành Bất biến (Operator & Coordinator Rules)

1. **CẤM CHỮA CHÁY TẠM THỜI QUA ADB:**
   - Khi nhận alert `[MÁY N]`, không chỉ dừng ở việc dùng ADB để mở lại app hay gỡ lock. BẮT BUỘC điều tra và sửa triệt để trong script codebase.
2. **LỆNH TRÍCH XUẤT DUY NHẤT (CẤM GREP TOÀN BỘ CODEBASE):**
   - Chỉ dùng: `python D:/Taadaa/tools/inspect_machine.py <N>`.
   - CẤM TUYỆT ĐỐI dùng `grep -rn`, `find`, `os.walk`, `glob(recursive=True)` quét diện rộng thư mục/ổ đĩa.
3. **QUY TẮC SUBAGENT DELEGATION:**
   - Subagent của Hermes chạy hoàn toàn background.
   - **CẤM DÙNG VÒNG LẶP `sleep` ĐỂ ĐỢI WORKER.** Dispatch xong phải báo cáo ngắn gọn ngay cho user và giữ session sẵn sàng tương tác; khi worker xong kết quả sẽ tự động đẩy vào hội thoại.
4. **KIỂM CHỨNG 2 TẦNG BẮT BUỘC:**
   - **Tầng 1 (Unit Test):** `pytest python_runner/tests/test_before_swipe_launcher_recovery.py -v` (< 30s).
   - **Tầng 2 (Live Canary):** Chạy canary thực tế trên đúng serial/máy lỗi (`run_tiktok.py` hoặc `run-feed-session.ps1 -Machines <N>`).
