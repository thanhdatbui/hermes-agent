# Google OAuth Account Chooser vs Consent Header Collision & GPM ProfilePath Matching

## 1. Google OAuth Account Chooser vs Consent Header Collision (2026-09-05)

### Triệu chứng & Hiện tượng
Khi tự động hóa luồng OAuth Antigravity/Google (`add_oauth_omniroute.py`):
```text
[INFO] Click chọn tài khoản: user@gmail.com
[INFO] Click chọn tài khoản: user@gmail.com
...
[WARNING] Không nhận được callback OAuth code trong thời gian chờ (timeout_stuck)
```
Browser mở lên, chọn được tài khoản Google, nhưng sau đó kẹt lặp lại việc click vào tài khoản mỗi 3 giây cho đến khi hết timeout 45s mà không bao giờ bấm được nút "Tiếp tục" / "Cho phép" (Consent).

### Root Cause
Trong vòng lặp xử lý DOM:
```python
# 3. Xử lý màn hình chọn tài khoản (Account Chooser)
acc_match = page.locator(f'div[data-identifier="{email}"], div:has-text("{email}")')
if acc_match.count() > 0:
    logger.info(f"Click chọn tài khoản: {email}")
    acc_match.first.click()
    time.sleep(3)
    continue
```
Selector `div:has-text("{email}")` quá rộng.
Khi Google chuyển từ màn hình Account Chooser sang màn hình Consent (cấp quyền truy cập cho ứng dụng), Google hiển thị user email ở thanh header/chip thông tin người dùng (`<header>` hoặc `<div>`).
Do đó, `div:has-text("{email}")` vẫn luôn khớp với thẻ `div` bọc email ở header trên màn hình Consent!
Lệnh `acc_match.first.click()` bấm vào header này rồi gọi `continue`, khiến vòng lặp nhảy ngược lên đầu và **HOÀN TOÀN KHÔNG BAO GIỜ CHẠY XUỐNG BƯỚC 5 (Consent / Tiếp tục / Cho phép)**.

### Giải pháp bắt buộc
1. **Loại bỏ selector broad text cho account chooser:**
   - Không dùng `div:has-text("{email}")`.
   - Dùng selector định danh chính xác của Google: `div[data-identifier="{email}"]`, `li[data-identifier="{email}"]`, hoặc `div[role="link"][data-identifier="{email}"]`.
2. **Kiểm tra Consent trước khi chọn tài khoản (Inverted Priority Gate):**
   - Trước khi kiểm tra Account Chooser, kiểm tra xem trang đã xuất hiện nút đồng ý cấp quyền (`button:has-text("Tiếp tục")`, `button:has-text("Continue")`, `button:has-text("Sign in")`, `#submit_approve_access`) hay chưa. Nếu đã có nút Consent thì bỏ qua bước chọn tài khoản.

---

## 2. Truy vấn Profile GPM bằng `ProfilePath` (Hash Folders)

### Triệu chứng
Khi chạy lệnh:
```bash
python add_oauth_omniroute.py --profile "OaQGVGQ0XU-05092026"
```
Script báo lỗi: `Không tìm thấy profile nào khớp với: OaQGVGQ0XU-05092026`.

### Root Cause
Trong SQLite `profile_data.db` của GPMLogin:
- Cột `Id`: UUID (ví dụ `3a7322d2-c10a-48bf-8334-406a384c11c0`).
- Cột `Name`: Tên hiển thị (ví dụ `10 - thachnha1103199810@gmail.com - 5112`).
- Cột `ProfilePath`: Tên thư mục vật lý (ví dụ `OaQGVGQ0XU-05092026`).

Nếu logic lọc tham số `--profile` chỉ so sánh `target_name in p["name"].lower() or target_name == p["id"].lower()`, các chuỗi mã hash thư mục `profile_path` sẽ không bao giờ khớp.

### Giải pháp bắt buộc
Luôn đối soát cả 3 trường `Name`, `Id` và `ProfilePath`:
```python
target_profiles = [
    p for p in GPMProfileManager.get_profiles_from_db()
    if target_name in p["name"].lower() or target_name == p["id"].lower() or target_name in p.get("profile_path", "").lower()
]
```
Điều này đảm bảo người dùng hoặc coordinator có thể chỉ định profile theo tên, UUID hoặc mã thư mục hash (`ProfilePath`) một cách thông suốt.
