# Samsung S7 MTP Popup Permanent Disable & TikTok 8-Account Hidden Button Pitfalls (2026-09-20)

## 1. Samsung USBConnection MTP Popup Permanent Disable
### Hiện tượng
- Khi cắm cáp USB hoặc nguồn sạc/hub chập chờn, điện thoại Samsung Galaxy S7 tự động bung dialog hệ thống:
  `com.samsung.android.MtpApplication/.USBConnection`
  *"Chú ý: Thiết bị được kết nối không thể truy cập dữ liệu trên thiết bị này..."*
- Dialog này chiếm trọn foreground, chặn các thao tác UIAutomator/ATX và làm nghẽn kết nối ADB dẫn đến lỗi `[adb-timeout] device=... timeout=20`.

### Giải pháp triệt để vĩnh viễn
- Thay vì chỉ tap "Hủy" (Cancel) hoặc phím BACK tạm thời (vẫn sẽ hiện lại khi reset bus USB), vô hiệu hóa tận gốc package hệ thống trên toàn farm:
  ```bash
  adb -s <serial> shell pm disable-user --user 0 com.samsung.android.MtpApplication
  ```
- Kết quả: Package chuyển sang trạng thái `disabled-user`. Popup biến mất vĩnh viễn, không bao giờ hiện lại khi cắm rút cáp hay reboot máy.

---

## 2. TikTok 8-Account Limit & Ẩn Nút "Thêm tài khoản" Trên Switcher (v46.x)
### Hiện tượng
Khi chạy reg bù (ví dụ Row 8) trên máy đã có 7 tài khoản trong bảng tính, batch runner gặp 2 nhóm lỗi:
1. `[04_add_account] MACHINE_FULL_8_ACCOUNTS: Thiết bị đã đạt giới hạn 8 tài khoản TikTok`
2. `[04_add_account] Không tìm thấy: ('Thêm tài khoản', 'Add account'...)`

### Phân tích Root Cause Thống Nhất
- **Bản chất cả 2 lỗi là một:** Thiết bị thực tế trên farm đã có đủ 8 tài khoản (do còn sót tài khoản ký sinh hoặc nick cũ chưa logout từ các đợt reseed trước, ví dụ `@vjorariw1hg` trên M2, `@yazmixpy2he` trên M4).
- Khi chạm trần 8 tài khoản, **TikTok tự động ẩn hoàn toàn nút "Thêm tài khoản"** khỏi bottom-sheet Switcher.
- **Vì sao báo 2 lỗi khác nhau:**
  - Trên TikTok bản cũ: Danh sách tài khoản mang resource-id nằm trong danh sách hardcode `["n72", "lkp", "l9b", "lpw", "l_z", "lrq", "lli"]` $\rightarrow$ hàm đếm `_acc_count` nhận diện đủ $\ge 8$ nick và ném `MACHINE_FULL_8_ACCOUNTS`.
  - Trên TikTok bản mới (v46.x): Resource-id bị obfuscate đổi sang `omm`, `omr`, `onj`, `oms`... $\rightarrow$ `_acc_count` đếm ra `0`. Nhưng vì nút "Thêm tài khoản" đã bị TikTok ẩn $\rightarrow$ `find_text_tap` không tìm thấy $\rightarrow$ rơi xuống ném `Không tìm thấy: ('Thêm tài khoản'...)`.

### Quy tắc xử lý & Phòng ngừa
1. **Kiểm tra nick ký sinh / nick dư:**
   - Đối chiếu danh sách nicks trong Switcher với Master DAT và `Tik1..7.xlsx`.
   - Nếu nick dư là tài sản user (đã reg dở hoặc còn LIVE): Ưu tiên backfill vào Row 8 trong workbook thay vì reg mới.
   - Nếu cần reg mới: Bắt buộc đăng xuất nick dư ra khỏi máy (đưa tổng nick về 7) trước khi chạy reg.
2. **Cập nhật hàm `tap_add_account` trong `social_reg_v1.py`:**
   - Đếm tài khoản linh hoạt bằng các container item của RecyclerView thay vì hardcode cụm resource-id cũ.
   - Bổ sung bước scroll/swipe up bottom-sheet (`input swipe 540 1500 540 700 250`) khi có 6–7 tài khoản để bảo đảm nút "Thêm tài khoản" không bị che khuất dưới mép màn hình.
