# Quy Trình Tự Động Đăng Nhập Lại Khi Văng / Thiếu Acc Trong Feed Session (User chốt 2026-09-21)

## 🛑 NGUYÊN TẮC BẮT BIẾN (USER RULE)
> "Ủa chứ bị văng acc thì sao k gọi script tiktok log in đăng nhập lại acc bị văng"

Khi máy gặp lỗi văng nick / thiếu nick trên thiết bị (`account-switcher-missing-expected`, `ACCOUNT_MISSING`, mất phiên):
- **CẤM TUYỆT ĐỐI** Coordinator chỉ dừng lại ở báo cáo hiện trường bị động hoặc hỏi user mà không đề xuất/chạy ngay lệnh đăng nhập lại.
- **BẮT BUỘC** gọi ngay công cụ đăng nhập chuẩn của Farm (`tiktok_login_v1.py` hoặc `reconcile_tiktok_accounts.py`) để nạp lại nick cho thiết bị, đảm bảo fleet luôn đủ slot hoạt động.

---

## 🔍 QUY TRÌNH 3 BƯỚC XỬ LÝ CHUẨN

### Bước 1: Inspect Switcher Thực Tế O(1) & Kiểm Tra Số Lượng Nick
- Dùng `atx-agent` dump hierarchy hoặc chụp ảnh màn hình Switcher + WinRT OCR (`windows-native-ocr`).
- **Phát hiện False Positive / Lệch Mapping**:
  - Không vội kết luận nick bị văng chỉ qua log alert! Có trường hợp nick báo lỗi trong batch (ví dụ Slot 7) thực tế **vẫn đang đăng nhập LIVE trong máy**, nhưng máy bị thiếu một nick ở slot khác (ví dụ Slot 3), hoặc SQLite `tiktok_tracker.db` bị lệch mapping giữa các slot.
  - So khớp 7-8 nick đang hiển thị trên Switcher với `taikhoan_run_safe.xlsx` và `taikhoan_dat_v2_updated .xlsx` để tìm ra **chính xác nick nào đang thiếu**.

### Bước 2: Cập Nhật Chuẩn Hóa Database Mapping (Nếu Lệch)
- Nếu bảng `farm_account_info` / `account_mapping` trong `D:/Taadaa/data/tiktok_tracker.db` bị gán sai `tik` (slot):
  ```python
  import sqlite3
  conn = sqlite3.connect('D:/Taadaa/data/tiktok_tracker.db')
  cur = conn.cursor()
  cur.execute("UPDATE farm_account_info SET tik = ? WHERE username = ? AND may = ?", (correct_slot, username, machine_id))
  cur.execute("UPDATE account_mapping SET tik = ? WHERE username = ? AND may = ?", (correct_slot, username, machine_id))
  conn.commit()
  conn.close()
  ```

### Bước 3: Gọi Script Đăng Nhập Chính Thức Để Nạp Lại Nick
- Chạy lệnh đăng nhập đơn lẻ chính thức của Farm từ `D:/Taadaa/Tiktok_Reg`:
  ```bash
  python D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py <MACHINE_ID> --email <USERNAME_OR_EMAIL> --ss
  ```
- **Lưu ý thực thi**:
  - Script `tiktok_login_v1.py` đã tích hợp tự đọc TOTP secret từ workbook và tự động đọc email OTP (Hotmail/Gmail).
  - Không được ngắt giữa chừng khi script đang ở bước 2FA.
  - Sau khi đăng nhập xong, chụp ảnh Switcher nghiệm thu xác nhận tài khoản đã xuất hiện trong danh sách.

---

## ⚠️ PITFALLS CẦN TRÁNH
1. **Lỗi môi trường venv trong Auto-Login Recovery (`_maybe_recover_missing_account_via_login`)**:
   - Trong `feed_swipe_smoke.py`, hàm `_maybe_recover_missing_account_via_login` mặc định trỏ tới `DEFAULT_RECONCILE_PYTHON = "D:/Taadaa/python-envs/tiktok-reg-recovery/Scripts/python.exe"`.
   - Nếu venv này bị lỗi package chéo (ví dụ `ImportError: cannot import name '_imaging' from 'PIL'`), tiến trình con sẽ crash và fail âm thầm.
   - Khi đó, Coordinator phải dispatch worker chạy trực tiếp bằng `tiktok_login_v1.py` qua môi trường python sạch của hệ thống.
2. **Tránh kẹt tiến trình I/O ngầm**:
   - Cấm chạy `grep -rn` quét diện rộng ổ đĩa D: hoặc các file workbook Excel lớn, vì trên Windows MSYS git-bash lệnh `grep.exe` sẽ bị treo và nuốt CPU, gây timeout các subagent chạy sau. Luôn dùng script Python O(1) chuyên dụng.
