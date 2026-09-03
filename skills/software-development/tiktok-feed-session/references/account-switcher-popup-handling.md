# Account Switcher & Popup Handling Lessons (Preflight & Navigation)

### 1. Nick mục tiêu đã `selected="true"` trong Account Switcher sheet
- **Hiện tượng:** Khi tài khoản mục tiêu đã ở trạng thái được chọn (có dấu tích đỏ ✔, XML attribute `selected="true"` hoặc `checked="true"`), script gửi lệnh tap vào nick mục tiêu sẽ **không** làm bảng modal "Chuyển đổi tài khoản" (Bottom Sheet) biến mất.
- **Hậu quả:** Bottom navigation bar ("Hồ sơ", "Trang chủ"...) tiếp tục bị che khuất, dẫn tới lỗi `navigation target profile not found in XML`.
- **Giải pháp:** Trong `_find_account_switch_option` hoặc trước khi tap tài khoản, kiểm tra xem element đã có `selected="true"` / `checked="true"` chưa. Nếu đã active, gửi phím **BACK** (`input keyevent 4`) để đóng modal sheet thay vì tap lặp lại.

### 2. Popup "Tài khoản của bạn cần được cập nhật" (`account_update_prompt`)
- **Vị trí cấu hình chuẩn:** Tầng `automation-core` (`src/automation_core/tiktok/benign_popup.py`) định nghĩa `ACCOUNT_UPDATE_PROMPT_SCREEN = "manual-needed:account-update-prompt"`.
- **Hành vi xử lý:** Phát hiện popup với tiêu đề *"Tài khoản của bạn cần được cập nhật"* và nội dung bảo mật, chọn hành động `dismiss_later_button` để bấm *"Để sau"*, giải phóng giao diện cho bước điều hướng tiếp theo.
