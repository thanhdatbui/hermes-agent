# GPMLogin Profile Groups & Live-Ready Mapping

## 1. Vị trí CSDL & Bảng dữ liệu
- File CSDL SQLite: `C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\profile_data.db`
- Bảng nhóm: `groups (id, name)`
- Bảng profile: `profiles (id, name, raw_proxy, GroupId, ...)`

## 2. Bảng phân nhóm Canonical (Group Mapping)
| Group ID | Tên Group | Số lượng (tham chiếu) | Ý nghĩa & Vai trò hệ thống |
| :---: | :--- | :---: | :--- |
| **1** | **All** | ~165 | Nhóm mặc định khi import/tạo profile mới hoặc chưa phân loại. |
| **10** | **Google_Live_Ready** | ~71 | Profile Gmail đã đăng nhập Google thành công, session LIVE 100%. |
| **11** | **Google_Cooldown_Error** | ~18 | Profile bị lỗi session, văng pass, checkpoint hoặc đang chờ cooldown 7 ngày. |
| **2 - 9** | *demo, loi tele, run, Linke, VNETSY, amazon, X, cheat* | 0 | Các group rỗng / legacy không sử dụng trong pipeline. |

## 3. Bất biến kiến trúc & Khóa an toàn Group 10
- **Khóa Cron nuôi (`cron_gpm_gmail_nurture.py`)**:
  - BẮT BUỘC chỉ bốc các profile thuộc `GroupId == 10`.
  - Tuyệt đối cấm bốc Group 1 hoặc Group 11 để lướt YouTube/News vì sẽ kích hoạt checkpoint xác minh Google.
- **Khóa Watchdog 2FA (`post_morning_gmail_2fa_watchdog.py`)**:
  - Chỉ quét và bật 2FA cho các tài khoản nằm trong Group 10.
  - Tuyệt đối cấm tự ý spawn profile GPM mới cho tài khoản chưa login.
- **Săn link Google One / AI Premium**:
  - Chỉ phân phối link vào các profile thuộc Group 10 để đảm bảo tốc độ nhận link qua CDP WebSocket (< 5s/link).
