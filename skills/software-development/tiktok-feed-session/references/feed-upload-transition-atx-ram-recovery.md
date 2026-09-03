# Chẩn đoán & Xử lý Timeout Hook Upload Video cuối Phiên 3 (Feed -> Upload Transition)

## 1. Hiện tượng & Bối cảnh
- Khi kết thúc phiên 3 của ca nuôi nick (feed-session), worker gọi upload hook để đăng video (`run_post.py` / `scripts.tiktok_workflow`).
- Hàng loạt máy (hoặc toàn bộ) bị rơi vào trạng thái `status: timeout`, `reason: upload-timeout` (chờ đủ 900s mà không đăng được video nào).

## 2. Nguyên nhân gốc rễ (Root Cause)
1. **Tràn RAM & Crash ngầm ATX (Low Memory Killer):**
   - Sau khi lướt feed 15-20 phút liên tục trong Phiên 3, app TikTok ngốn dung lượng RAM rất lớn trên các thiết bị Android yếu (Samsung S7 / Android 7).
   - Hệ điều hành Android tự động kill tiến trình `atx-agent` / `uiautomator stub` (Exit code 137 / SIGKILL) để giữ TikTok không bị crash.
   - Khi upload hook vừa được khởi chạy, nó yêu cầu kết nối lại ATX (Port 7912) để xác thực màn hình `WAIT_FEED`. Do ATX đã bị kill, nó liên tục gặp lỗi `ATX_SESSION_UNAVAILABLE` và bị kẹt ở vòng lặp `Waiting for feed/home (timeout=90s)`.
2. **Kẹt Prompt Non-Interactive (nếu gọi trực tiếp CLI):**
   - `run_post.py` có prompt `Type 'YES' to continue`. Nếu stdin không phải TTY hoặc không được pipe token xác nhận, subprocess sẽ bị `EOFError` hoặc treo chờ input.

## 3. Quy trình chuẩn bị & Khắc phục bắt buộc (Feed -> Upload Transition)
Trước khi bước vào khâu upload video cuối ca hoặc khi kích hoạt upload hook:
1. **Force-stop app TikTok cũ:**
   `adb -s <serial> shell am force-stop com.ss.android.ugc.trill`
   -> Giải phóng 100% RAM bị chiếm dụng sau phiên lướt feed dài.
2. **Làm sạch & Khởi động lại dịch vụ ATX:**
   `adb -s <serial> shell pkill -9 -f uiautomator`
   `adb -s <serial> shell /data/local/tmp/atx-agent server -d`
3. **Bypass prompt confirmation:**
   Đảm bảo `run_post.py` tự động nhận `confirmation = "YES"` khi chạy non-interactive hoặc bọc trong try/except `(EOFError, OSError)`.
4. **Mở lại TikTok sạch:**
   Khởi động lại app TikTok từ đầu để vào thẳng luồng upload với bộ nhớ trống và kết nối ATX ổn định.
