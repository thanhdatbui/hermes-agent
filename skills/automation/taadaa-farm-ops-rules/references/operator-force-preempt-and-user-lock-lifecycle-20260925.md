# Operator Force Preempt & User-Locked Machine Session Lifecycle (2026-09-25)

## 1. Bối cảnh & Vấn đề (The Deadlock Trap)
- **Hiện tượng:** Khi một máy farm đang chạy phiên nền (ví dụ: `run_tiktok.py --mode multi-machine-feed-session reservation`), tiến trình này tạo file lock JSON (`machine_N.lock.json` và `serial_xxx.lock.json`) với `user_authorized=True`, `pinned=True`, `ttl_seconds=3600`.
- **Bẫy:** Khi User cần can thiệp khẩn cấp (như đổi avatar, sửa profile, cứu hộ tài khoản), Agent/Coordinator kiểm tra thấy lock đang active nên từ chối chạy hoặc báo bị kẹt lock.
- **Rủi ro hồi quy:** Trong `automation_core/device_lock.py`, trước đây `_takeover_payload` chặn 100% các request takeover nếu lock có `pinned=True` hoặc `user_authorized=True` bất kể tiến trình owner đã chết hay còn sống, làm gãy 13 unit tests của `test_device_lock.py`.

---

## 2. Giải pháp Kiến trúc & Triển khai

### A. Core Lock Takeover Logic (`automation_core/device_lock.py`)
1. **Quyền Operator Preempt Thắng Tuyệt Đối (`force_preempt=True` / `TAKEOVER_SCOPE_OPERATOR_PREEMPT`):**
   - Khi User ra lệnh can thiệp trên máy cụ thể, Agent được phép dùng `force_preempt=True` để lập tức chiếm lock đè lên tiến trình cũ.
2. **Khôi phục Recovery Scopes cho Pinned Locks Đã Inactive/Dead:**
   - Nếu `pinned=True` nhưng tiến trình owner đã chết (`alive is False`) hoặc đã inactive (`owner_active is False` và status không thuộc active wire statuses), các scope phục hồi tự động (`SAME_PROJECT_RECOVERY`, `FULL_SCOPE_TAKEOVER`) được phép reclaim bình thường mà không bị chặn nhầm.

### B. Vòng đời Khóa User-Locked Machine (User Lock Session Lifecycle)
- **Tự động chiếm lock:** Khi User yêu cầu can thiệp -> Acquire lock dạng `OPERATOR_PREEMPT` / `user_authorized=True` / `pinned=True`.
- **Miễn nhiễm hoàn toàn với Cronjob:**
  - `reap-dead-owner-locks.py` và `farm_idle_screen_and_app_healer.py` bắt buộc bỏ qua các lock có `pinned=True` / `user_authorized=True` / `status='user_reserved'`. Tuyệt đối không tự động force-stop TikTok hay xóa lock của máy đang được User chỉ định can thiệp.
- **Tự động nhả lock khi Chốt phiên (`session-close-protocol`):**
  - Không bắt User phải nhớ gõ lệnh `release`.
  - Giữ nguyên lock trong suốt phiên làm việc. Khi User ra lệnh chốt phiên (`"chốt phiên"`, `"đóng phiên"`, `"kết thúc phiên"`), bước teardown của closeout protocol sẽ quét và giải phóng toàn bộ lock thiết bị trả về cho scheduler farm.

---

## 3. Bài học Kiểm chứng Bằng chứng Avatar & Profile (Evidence Discipline)
- **Bẫy False-Success Avatar (`verified=True` / `exit=0`):**
  - Tool runner báo `exit=0, verified=True` chỉ chứng minh thao tác click nút Lưu/Crop đã gửi đi thành công, KHÔNG chứng minh avatar đã được CDN TikTok cập nhật lên đúng profile.
  - Sau khi crop/lưu avatar, TikTok có thể tự động đổi view sang tài khoản khác trong switcher hoặc cache hiển thị avatar xám / icon mặc định.
- **Điều kiện nghiệm thu BẮT BUỘC:**
  1. Mở lại đúng màn hình Profile của đúng handle `@username` mục tiêu.
  2. Chụp ảnh fresh và OCR đọc lại tên hiển thị + `@username`.
  3. Kiểm tra vòng tròn Avatar: Pixel variance / màu sắc phải chứa ảnh thật của đối tượng, không được là icon silhouette / camera mặc định / màn hình đen / ảnh của nick khác.
