# AI Auto-Recovery & Git Mutex (`git_lock_busy`)

## 1. Cơ chế vận hành
Trong pipeline AI Auto-Recovery của repo `tiktok-luot nuoi acc` (`python_runner/ai_recovery/code_patcher.py`):
- Khi các máy nuôi tài khoản gặp sự cố UI không xác định, Producer gửi alert và ảnh chụp màn hình lên kênh Telegram `Farm Alerts`.
- Bot Hermes tiếp nhận và thực hiện phân tích vision, sau đó điều khiển ADB gỡ kẹt tại hiện trường và sinh code handler mới bổ sung vào `benign_popup.py` hoặc `feed_swipe_smoke.py`.
- Để tránh xung đột khi nhiều worker trên nhiều máy cùng sửa file, chạy pytest và git commit/push đồng thời, module `code_patcher.py` sử dụng một file mutex:
  `D:\Taadaa\runtime\kibe\git_patch.lock` (với TTL mặc định 600 giây = 10 phút).

## 2. Nguyên nhân xuất hiện mã `❌ git_lock_busy`
- Khi có ít nhất 2 máy cùng kích hoạt Auto-Recovery trong cùng một khoảng thời gian ngắn:
  - Máy A xin được lock trước và đang thực hiện quy trình `patch -> pytest -> git commit & push`.
  - Máy B kiểm tra `_acquire_git_lock()` thấy lock đang bị chiếm giữ (age < TTL) nên trả về `False` và gán mã lỗi `error: "git_lock_busy"`.

## 3. Tác động và cách xử lý
- **Thao tác cứu máy (Live recovery):** Vẫn được thực hiện bình thường (ADB click / back / keyevent) và máy vẫn tự động tiếp tục tiến trình nuôi nick (Resume).
- **Thao tác mã nguồn (Repo patch):** Chỉ bị bỏ qua bước auto-commit vào master nhằm bảo vệ an toàn cho working tree và tránh git conflict khi nhiều máy cạnh tranh.
- **Xác nhận trạng thái:** Khi tiến trình của máy A hoàn tất, lock sẽ tự động được giải phóng (`GIT_PATCH_LOCK.unlink()`).
