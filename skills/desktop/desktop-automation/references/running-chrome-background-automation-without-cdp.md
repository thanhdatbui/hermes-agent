# Running Chrome Background Automation via `computer_use` Without CDP Port 9222

## Context & Problem
- Khi cần thao tác trên Google Chrome (ví dụ: tìm kiếm sàn thương mại điện tử Shopee, kiểm tra tài khoản cá nhân, xem tab web) dưới profile đang đăng nhập của User (profile `jinrakal` / `Profile 4`).
- Thông thường, quy trình CDP yêu cầu Chrome khởi chạy với `--remote-debugging-port=9222`.
- **Tuy nhiên, khi Chrome đã được User mở sẵn từ trước mà không có cờ 9222:**
  - Lệnh khởi chạy Chrome mới với `--remote-debugging-port=9222` sẽ bị Chrome tự động delegate về tiến trình đang chạy $\to$ Cổng 9222 **KHÔNG** được lắng nghe (`WinError 10061`).
  - Lệnh `taskkill` hoặc đóng Chrome của User sẽ làm mất các tab đang làm việc dở dang, phiên khôi phục bị crash.
  - Guard của Coordinator có thể chặn các lệnh terminal cấp thấp (`powershell Stop-Process`, `taskkill`).

## The Solution: CUA Background Driver + UIA ValuePattern
Sử dụng `computer_use` điều khiển cửa sổ Chrome đang chạy hoàn toàn trong nền mà không cần mở port CDP 9222:

### Step-by-step Workflow:
1. **Xác định Window Target:**
   - Gọi `computer_use(action='list_windows')` tìm cửa sổ `chrome.exe` chứa profile mong muốn (tiêu đề cửa sổ hoặc profile icon).
   - Lấy đúng `pid` và `window_id`.

2. **Capture Cây Tương Tác (SOM):**
   - Gọi `computer_use(action='capture', mode='som', pid=<pid>, window_id=<window_id>)`.
   - Xác định chỉ số element của:
     - Nút mở tab mới: `label: 'Thẻ mới'` (nút `+` trên tab bar).
     - Thanh địa chỉ: `label: 'Thanh địa chỉ và tìm kiếm'`, `role: 'Edit'`.

3. **Mở Tab & Điều Hướng Không Trộm Focus:**
   - Click mở tab mới: `computer_use(action='click', element=<index_the_moi>)`.
   - Đặt URL vào thanh địa chỉ bằng **UIA ValuePattern**:
     `computer_use(action='set_value', element=<index_address_bar>, value='https://shopee.vn/search?keyword=...')`.
     *(Lưu ý: Không dùng `action='type'` hay `action='key'` vì trên Chrome background UIA sẽ báo `background_unavailable` đòi foreground. `set_value` hoạt động êm ái trong nền 100%).*

4. **Kích Hoạt Tìm Kiếm:**
   - Sau khi `set_value`, chụp lại capture SOM. Thanh Omnibox sẽ hiển thị dropdown gợi ý URL (`Omnibox Popup` $\to$ `ListItem` URL).
   - Click vào element gợi ý đó (`computer_use(action='click', element=<index_dropdown_item>)`) hoặc click nút Search trên web nếu đã ở trong trang.

5. **Đọc Dữ Liệu & Nghiệm Thu:**
   - Dùng `capture(mode='som')` kết hợp `vision_analysis` để đọc trực tiếp nội dung trang đã load.
   - Thao tác click trên trang web có thể thực hiện trực tiếp theo số index của các item trong SOM tree.
