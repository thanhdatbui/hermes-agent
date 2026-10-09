# GPM Profile Standardization, Proxy Mapping & Verification Gates

## 1. Chuẩn Hóa Đặt Tên Profile GPM: `<Số_Máy> - <Gmail> - <Port>`
Tên Profile GPM trong cơ sở dữ liệu `profile_data.db` (cột `Profiles.Name` và key `JsonData['Name']`) và `master_gmail_manager.xlsx` bắt buộc tuân theo cấu trúc:
```
<Số_Máy> - <Gmail> - <Port>
```

### Ví dụ chuẩn hóa:
- **Profile đơn:** `03 - lequynh27032002@gmail.com - 5103`
- **Profile máy đa tài khoản (Legacy + Clean song song):**
  - Clean profile: `01 - duongkien12022001@gmail.com - 5101`
  - Legacy profile: `01 - thanhdatbui19951@gmail.com - 5101` (lấy theo Gmail phụ đang live bên trong)
- **Profile dải Admin Pool:** `10008 - marcusephillips52sns@gmail.com - 10008`

---

## 2. Quy Tắc Gán Proxy S7 Bất Biến (Cấm Gán Lung Tung)
Proxy của mỗi profile bắt buộc phải tương ứng đúng với số máy S7 chứa Gmail đó trên dàn điện thoại:
1. **Gán Proxy Trước Khi Bật Trình Duyệt:** Bắt buộc truyền `raw_proxy` ngay trong payload `POST /api/v3/profiles/create` để Chromium khởi chạy với `--proxy-server` từ mili-giây đầu tiên. Cấm bật browser bằng IP mạng nhà rồi mới login.
2. **Kỷ Luật Đóng Profile Tức Thì:** Mọi luồng sau khi chạy xong (thành công hay fail) đều phải gọi `stop_profile` trong khối `finally` để đóng sạch cửa sổ, tránh mở ngâm hàng loạt.
3. **Dàn S7 Máy 1..8:** `test.taadaa.click:5101`..`5108` (`mobi1`..`mobi8` / Singbox `20001`..`20008`).
4. **Dàn S7 Máy 9:** `test.taadaa.click:5111` (`mobi11` / Singbox `20011`) — *Lưu ý: Không tồn tại port 5109 và 5110*.
5. **Dàn S7 Máy 10..16:** `test.taadaa.click:5112`..`5118` (`mobi12`..`mobi18` / Singbox `20012`..`20018`).
6. **Dàn S7 Máy 17..32:** `test.taadaa.click:5121`..`5138` (`mobi21`..`mobi38` / Singbox `20017`..`20032`).
7. **Dàn S7 Máy 41, 42, 60:**
   - Máy 41 $\rightarrow$ `test.taadaa.click:5103` (`mobi3` / Singbox `20003`).
   - Máy 42 $\rightarrow$ `test.taadaa.click:5104` (`mobi4` / Singbox `20004`).
   - Máy 60 $\rightarrow$ `test.taadaa.click:5126` (`mobi26` / Singbox `20026`).
8. **Dàn S7 Máy 70, 71:**
   - Máy 70 $\rightarrow$ `test.taadaa.click:5138` (`mobi38` / Singbox `20070`).
   - Máy 71 $\rightarrow$ `mirotik1.taadaa.click:10006` (Singbox `20071`).
9. **CẤM KỴ:** Tuyệt đối không gán proxy MikroTik Admin (`10008..10035`) cho tài khoản thuộc dàn S7 Farm.

---

## 3. Quy Tắc Verification-First Naming (Chỉ Đổi Tên Khi Đã Verify Live)
Khi nhập (import) hoặc khôi phục (restore) các profile cũ từ đĩa:
1. **Không đổi tên trước khi mở:** Giữ nguyên tên ban đầu hoặc tên tạm (ví dụ `20`, `21`...).
2. **Khởi chạy profile qua Local API v3:** Mở browser, kết nối Playwright CDP vào `https://myaccount.google.com/`.
3. **Xác thực trạng thái trong DOM:**
   - Nếu URL là `myaccount.google.com` và DOM chứa thông tin tài khoản hợp lệ $\rightarrow$ **LIVE** $\rightarrow$ Đổi tên thành `<Số_Máy> - <Gmail> - <Port>`.
   - Nếu bị chuyển hướng về trang đăng nhập (`accounts.google.com/v3/signin`) hoặc dính checkpoint (`challenge/iap`) $\rightarrow$ **GIỮ NGUYÊN TÊN CHƯA ĐỔI**, ghi nhận trạng thái Expired/Checkpoint vào Excel.

---

## 4. Quy Trình Đồng Bộ Chuẩn Hóa Database & 4 Sheets Excel Master (`master_gmail_manager.xlsx`)
Khi thực hiện chuẩn hóa hàng loạt (Batch Standardization):
1. **Sao lưu trước khi chỉnh sửa (Timestamped Backups):**
   - SQLite DB: `C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\_backup\profile_data_backup_YYYYMMDD_HHMMSS.db`.
   - Master Excel: `D:\OneDrive\TaadaaData\kibe\_backup\master_gmail_manager_backup_YYYYMMDD_HHMMSS.xlsx`.
2. **Cập nhật đồng bộ SQLite `profile_data.db`:**
   - Cập nhật đồng thời 2 vị trí: Cột `Profiles.Name` và thuộc tính `JsonData['Name']`.
   - Bảo toàn nguyên vẹn 100% các trường hardware fingerprint trong `JsonData` (124/130 keys).
3. **Đồng bộ hóa 4 Sheet trong Excel Master:**
   - Cột `Tên Profile GPM` trên 4 Sheet (`Kibe_Farm_S7`, `Gmail_Dat`, `Master_All`, `Admin_GPM_Pool`) khớp 100% tên mới:
     * Dàn Farm S7: `<Số_Máy> - <Email> - <Port>` (Số máy 2 chữ số: `01`..`09`, `10`..`80`).
     * Dàn Admin: `<Port> - <Email> - <Port>` (VD: `10008 - marcusephillips52sns@gmail.com - 10008`).
     * AMZ: `AMZ_Main`.
     * Profile chưa verify / checkpoint: Giữ nguyên tên tạm (`20`, `21`, `70`, `71`...) cho đến khi verify live.
4. **Hậu kiểm (Post-write Verification):**
   - Kiểm tra `0 mismatches` giữa `Profiles.Name` và `JsonData['Name']`.
   - Đối soát mapping profile giữa DB và Excel đảm bảo tính toàn vẹn 100%.
