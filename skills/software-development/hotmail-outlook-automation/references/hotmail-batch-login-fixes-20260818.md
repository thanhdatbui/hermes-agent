# Session Notes: Hotmail Batch Login Fixes (2026-08-18)

## Bối cảnh & Mục tiêu
- Nạp 10 tài khoản Hotmail từ file cố định `D:\Taadaa\Hotmail\hotmail_input.txt` (loại 2 có token Graph API).
- Tự động chia đều cho các máy farm (1-80) có ít tài khoản TikTok nhất, điều kiện bắt buộc: **phải có Proxy hợp lệ trong `PROXYgandienthoai.xlsx`**.
- Sau khi log thành công lên Outlook app của máy: ghi thông tin vào `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx` (kèm refresh_token & client_id) và tự động xóa dòng đã xử lý khỏi `hotmail_input.txt`.

## Các lỗi đã phát hiện & Fix trực tiếp vào canonical script

### 1. ATX JSON-RPC gán cố định port 7912
- **Triệu chứng:** Khi chạy batch nhiều máy, `_atx_jsonrpc_call` gọi cứng `forward tcp:7912 tcp:7912` dẫn tới port collision và gọi nhầm máy khác.
- **Fix:** Bổ sung `_ensure_atx_local_port(adb, device)`: kiểm tra danh sách forward của ADB, lấy dynamic port đã mở cho serial đó hoặc mở port ngẫu nhiên `forward tcp:0 tcp:7912`.

### 2. Lệnh `ps -A` lỗi mã 127
- **Triệu chứng:** Hàm tìm PID UiAutomator `_atx_uiautomator_pid` chạy `run_adb(adb, device, "shell", "ps", "-A")` bị lỗi mã 127 trên một số thiết bị.
- **Fix:** Chuyển sang fallback `run_adb(adb, device, "ps")` / `run_adb(adb, device, "shell", "ps")`.

### 3. Nút TIẾP TỤC ở màn nhập email không ăn tap shell
- **Triệu chứng:** `_tap_outlook_app_id` gửi `input tap` qua adb shell bị trượt trên WebView màn hình `AddAccountActivity`.
- **Fix:** Đổi qua dùng `_atx_input_tap` (bấm bằng ATX JSON-RPC trực tiếp vào tâm node bounds).

### 4. Màn hình "Chọn loại tài khoản" xuất hiện sau khi nhập email
- **Triệu chứng:** Ở một số tài khoản/thiết bị, sau khi nhập email và bấm TIẾP TỤC, Outlook app nhảy về màn "Chọn loại tài khoản" (`ChooseAccountActivity`) thay vì sang màn nhập mật khẩu.
- **Fix:** Bổ sung bước kiểm tra `_outlook_app_account_type_selector_visible` sau khi submit email để tự động bấm vào entry "Outlook" và chuyển tiếp sang màn nhập mật khẩu.

### 5. Drawer mở sẵn hoặc chứa nhiều tài khoản
- **Triệu chứng:** Khi app đã có sẵn 1 tài khoản, drawer có thể mở sẵn hoặc thanh điều hướng hiển thị avatar của tài khoản vừa log mới nhưng header summary vẫn là tài khoản cũ.
- **Fix:** `outlook_app_identity_matches` kiểm tra cả text/content-desc của avatar node trên thanh điều hướng `account_navigation_view`.

### 6. Ghi nhận trạng thái `ALREADY_SIGNED_IN`
- **Fix:** Cập nhật `scripts/hotmail_list_runner.py` để ghi nhận cả `SUCCESS` lẫn `ALREADY_SIGNED_IN` vào `gmail_clean_v2.xlsx` và loại bỏ khỏi file nguồn.
