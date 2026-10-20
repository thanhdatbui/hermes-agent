# Điều Tra Nguồn Gốc Hotmail, Trạng Thái Token API & Tiến Trình Change Info GPM

Tài liệu hướng dẫn quy trình điều tra dứt khoát, chính xác khi người vận hành yêu cầu kiểm tra tài khoản Hotmail có Token API hay không, mua từ nguồn nào, tại sao chưa có token hoặc chưa được change info trên GPM.

---

## 1. Kiểm Tra Trạng Thái Token API Live (Cấm Suy Diễn, Đọc Trực Tiếp File)

Khi được hỏi tài khoản Hotmail có Token API Live hay không, **BẮT BUỘC** đọc trực tiếp dòng dữ liệu trong bảng tính, cấm suy diễn từ biến môi trường hay nói lý thuyết suông.

### Cấu trúc cột `D:/OneDrive/TaadaaData/kibe/gmail_clean_v2.xlsx` (Sheet `Gmail Accounts`):
* Cột 1: `số máy` (Machine ID)
* Cột 2: `tài khoản gmail` (Email)
* Cột 3: `pass mail` (Password hòm thư)
* Cột 5: `mail khôi phục` (Recovery Email)
* Cột 9: `token` (OAuth2 Refresh Token của Microsoft Graph)
* Cột 10: `client_id` (Azure Client ID, thường là `9e5f94bc-e8a4-4e73-b8be-63364c29d753`)

### Lệnh kiểm tra nhanh O(1):
```python
import openpyxl

wb = openpyxl.load_workbook(
    "D:/OneDrive/TaadaaData/kibe/gmail_clean_v2.xlsx", data_only=True
)
ws = wb["Gmail Accounts"]
for r in range(2, ws.max_row + 1):
  if str(ws.cell(row=r, column=2).value or "").strip().lower() == target_email:
    tok = ws.cell(row=r, column=9).value
    cid = ws.cell(row=r, column=10).value
    print(f"Row {r}: tok={tok!r}, client_id={cid!r}")
    break
```
* **Kết luận dứt khoát:**
  - Nếu Cột 9 & 10 có giá trị chuỗi -> Có token (thử verify live qua `verify_graph_token(refresh_token, client_id)`).
  - Nếu Cột 9 & 10 là `None` -> **KHÔNG CÓ Token API**, báo cáo rõ ràng không úp mở.

---

## 2. Phân Loại 2 Nguồn Tài Khoản Hotmail Trên Farm

Trên Farm Taadaa tồn tại 2 nhóm Hotmail với tính chất hoàn toàn khác nhau:

### Nhóm A: Mua Qua Tool/API Tự Động (`buy_hotmail.py` qua BoxTaiKhoan / CloneFBIG)
* **Định dạng lúc mua về:** 4-5 trường `email|pass|refresh_token|client_id(|recovery_email)`.
* **Đặc điểm:**
  - Luôn có sẵn Refresh Token và Client ID OAuth2 của Microsoft Graph.
  - Được lưu trữ trong các file log mua: `D:/Taadaa/Hotmail/latest_bought_*.txt`, `hotmail_all_60_bought.txt`, `hotmail_input.txt`.
  - Có thể đọc OTP tự động không cần trình duyệt bằng cách gọi Microsoft Graph API lấy mail mới nhất.

### Nhóm B: Hotmail Via / Clone Mua Lẻ Nhập Tay (Lô đầu tháng 08/2026)
* **Định dạng lúc mua về:** 3 trường `email|pass|recovery_email` (phần lớn mang đuôi `@fviainboxes.com`).
* **Đặc điểm:**
  - Cột 9 (`token`) và Cột 10 (`client_id`) trong Excel để trống (`None`).
  - **Không có trong các file mua tự động** `latest_bought_*.txt`.
  - Không bị "lưu bậy làm mất token", mà bản chất là gói mail cơ bản không kèm OAuth.
  - Lịch sử đăng ký TikTok ban đầu trong `D:/Taadaa/Tiktok_Reg/social_reg_log.txt` ghi nhận:
    `[otp-outlook-app] Non-Gmail target -> read via Outlook app` (phải đọc qua app Outlook điện thoại hoặc GPM, không đọc qua API Graph).

---

## 3. Điều Tra Lịch Sử GPM & Lý Do Chưa Được Change Info

Khi người dùng hỏi *"Login lên GPM lâu chưa mà chưa được change info (đổi pass / gỡ recovery)?"*:

### Bước 1: Tra cứu Profile GPM
Gọi API GPM Local (`127.0.0.1:19995`):
```python
import json, urllib.request

req = urllib.request.urlopen(
    "http://127.0.0.1:19995/api/v3/profiles?search="
    + email
    + "&page=1&per_page=10",
    timeout=5,
)
data = json.loads(req.read().decode("utf-8"))
for p in data["data"]:
  print(p["id"], p["name"], p["created_at"], p["raw_proxy"])
```
* **Lưu ý quan trọng:** Kiểm tra xem có nhiều profile trùng email hay không. Thường có profile cũ tạo ngày 29/09 dùng proxy MikroTik `10006`, và profile mới chuẩn hóa ngày 18/10 dùng proxy máy `192.168.110.2:200xx`.

### Bước 2: Kiểm tra trạng thái trong Tracker Đổi Pass
Đọc file state: `D:/Taadaa/runtime/kibe/cron-state/hotmail_changed_tracker.json`.
* Nếu email nằm trong `changed_emails`: Đã đổi pass thành công, có timestamp và method.
* Nếu email nằm trong `cooldowns`: Đang bị cooldown do lỗi tạm thời (24h).
* Nếu email chưa có trong file: Chưa được đổi pass.

### Bước 3: Nguyên nhân chưa tới lượt đổi pass:
1. **Cơ chế cuốn chiếu an toàn:** Watchdog đêm (`gpm_change_hotmail_security.py` / `cron_night_hotmail_security_watchdog.py`) chạy khung giờ 02:30 - 05:00 sáng, mỗi đợt chỉ chạy **1 - 3 tài khoản** để tránh Microsoft bật cờ checkpoint IP proxy hàng loạt.
2. **Điều kiện lọc khắt khe:**
   - Phải đủ tuổi ngâm >= 7 ngày.
   - Phải ĐÃ CÓ tài khoản TikTok (`user_val` và `pass_val` trong workbook).
   - Phải ĐÃ CÓ mật khẩu ChatGPT (Cột 12 `pass_chatgpt` trong `taikhoan_dat_v2_updated .xlsx`).
   - Profile GPM phải gán đúng proxy hiện tại của máy farm (các profile cũ mang proxy MikroTik `10006` sẽ bị bỏ qua).
