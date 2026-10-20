# Microsoft Hotmail Login UI Drift ("Use your password" vs "Use your password instead"), False-Positive Security Block, and Quarantine Rescue Protocol (2026-10-20)

## 1. Hiện Tượng & Tác Động Vận Hành
Trong đợt vận hành Farm Hotmail -> GPM -> ChatGPT tháng 10/2026:
- 119 tài khoản toàn farm bị rơi vào trạng thái `BLOCKED` (84 nick Kibe, 35 nick Admin).
- Trong đó, 3 tài khoản ở cụm Admin bị rơi vào trạng thái **`QUARANTINE`** (chết cứng, không bao giờ được supervisor tự động bốc chạy lại do `login_retry_count >= 3`).
- Báo cáo 6h ban đầu chỉ hiển thị một dòng tổng `⚠️ Lỗi / Kẹt cần cứu (BLOCKED): 119`, che giấu mất 3 nick QUARANTINE và không giải thích nguyên nhân lỗi cụ thể.

## 2. Truy Vết Gốc Rễ Qua WinRT OCR
Khi Coordinator chạy WinRT OCR trực tiếp lên các file chụp hiện trường thất bại (`post_login_218_...png` và `post_login_215_...png`), chữ trên màn hình được bóc tách:
```text
Verify your email
We'll send a code to xu*****@smvmail.com. To verify this is your email, enter it here.
Send code
Already received a code?
Use your password
Help and feedback | Terms of use | Privacy and cookies
```

### Điểm Gãy Kỹ Thuật (UI Drift):
1. **Thay đổi UI từ phía Microsoft:** Thay vì hiển thị nhãn cũ `"Use your password instead"`, Microsoft đã rút gọn nhãn liên kết thành **`"Use your password"`**.
2. **Selector bị trượt:** Script `batch_gpm_hotmail_password_login.py` chỉ tìm kiếm các selector:
   - `#idA_PWD_SwitchToPassword`
   - `a:has-text('Use your password instead')`
   - `text='Use your password instead'`
   - `a:has-text('Sử dụng mật khẩu của bạn')`
3. **Kích hoạt bẫy False-Positive Security Block:** Do không click được vào liên kết để chuyển sang ô nhập password `#i0118`, Playwright tiếp tục đứng ở màn hình yêu cầu xác minh email. Khi kiểm tra từ khóa cấm trong body text, script bắt trúng cụm `"verify your email"` (nằm trong danh sách `hard_block_keywords`), ngộ nhận là tài khoản bị khóa bảo vệ và trả về `SECURITY_BLOCK: verify your email` $\rightarrow$ Đẩy nick vào `BLOCKED` và sau 3 lần biến thành `QUARANTINE`.

## 3. Bản Vá Kỹ Thuật Chuẩn Hóa O(1)
Trong `D:/Taadaa/Hotmail/scripts/batch_gpm_hotmail_password_login.py`, mở rộng danh sách `switch_selectors`:
```python
switch_selectors = [
    "#idA_PWD_SwitchToPassword",
    "a:has-text('Use your password instead')",
    "a:has-text('Use your password')",
    "a:has-text('Sử dụng mật khẩu của bạn')",
    "a:has-text('Sử dụng mật khẩu')",
    "text='Use your password instead'",
    "text='Use your password'",
    "text='Sử dụng mật khẩu của bạn'",
    "text='Sử dụng mật khẩu'",
]
```

### Bằng Chứng Nghiệm Thu Canary:
- Chạy trực tiếp trên tài khoản đang bị kẹt `M218:xusluerrmba.hhiasn.1995.pulp@hotmail.com`:
  - Lệnh: `python D:/Taadaa/Hotmail/scripts/batch_gpm_hotmail_password_login.py --profile-id ... --email ... --password ... --proxy-port 10013 --raw-proxy 192.168.110.2:10013 --machine 218`
  - Kết quả: `LOGIN SUCCESS! (exit code 0)`
  - OCR ảnh `post_login_218_...png`: Đã vượt qua bước xác minh, xuất hiện màn hình `We're updating our terms` của tài khoản đăng nhập thành công.

## 4. Chuẩn Hóa Báo Cáo 6H & Giám Sát Nút Thắt
Để chống tái diễn tình trạng báo cáo thiếu thông tin:
1. **Bóc tách QUARANTINE:** Tách riêng số nick chết cứng do fail $\ge 3$ lần (`login_retry_count >= 3`) ngay dưới dòng `BLOCKED` để người quản trị biết nick cần kiểm tra lại pass.
2. **Minh bạch hóa nút thắt WAIT_7D:**
   - Đếm số lượng nick đã ngâm đủ $\ge 7$ ngày (`matured_7d`).
   - Đếm số lượng nick bị thiếu thông tin TikTok (`missing_tiktok`: `has_tiktok: False` hoặc `password: ''`).
   - **Quy tắc an toàn Supervisor:** CẤM cho tài khoản sang `CHANGE_INFO` khi chưa có tài khoản TikTok để tránh làm đứt gãy đồng bộ dữ liệu.
3. **Triệt tiêu cảnh báo ảo `DONE_WITHOUT_CHATGPT_REG`:** Hỗ trợ nhận diện cờ boolean `has_chatgpt: True` từ các batch lịch sử thay vì chỉ bắt buộc timestamp ISO `chatgpt_registered_at`.
4. **Chặn Delta ảo:** Khi snapshot trước rỗng hoặc khởi tạo lại với số 0, cấm in delta nhảy số gây mâu thuẫn với trạng thái farm idle.
