# Vô hiệu hóa vĩnh viễn Samsung MTP Popup & Xử lý ẩn nút "Thêm tài khoản" khi đạt 8 nick (2026-09-20)

## 1. Vô hiệu hóa vĩnh viễn Samsung USBConnection (MTP Popup)
- **Vấn đề**: Điện thoại Samsung S7 tự động bật popup `com.samsung.android.MtpApplication/.USBConnection` mỗi khi cắm cáp USB hoặc điện áp chập chờn. Modal này làm gián đoạn ADB bridge, dẫn tới lỗi `[adb-timeout] device=... timeout=20`.
- **Giải pháp triệt để**: Vô hiệu hóa tận gốc package hệ thống trên máy:
  ```bash
  adb -s <serial> shell pm disable-user --user 0 com.samsung.android.MtpApplication
  ```
- **Hiệu quả**: Không bao giờ tái phát khi cắm rút cáp USB hay khởi động lại thiết bị.

---

## 2. Bản chất đồng nhất giữa 2 lỗi: `MACHINE_FULL_8_ACCOUNTS` & `Không tìm thấy: ('Thêm tài khoản')`
- **Nguyên nhân cốt lõi**: Thiết bị đã chạm trần tối đa 8 tài khoản TikTok do còn sót nick cũ/ký sinh chưa được đăng xuất (ví dụ `@vjorariw1hg` trên Máy 2, `@yazmixpy2he` trên Máy 4).
- **Cơ chế ẩn của TikTok**: Khi đã có đủ 8 tài khoản, TikTok ẩn hoàn toàn nút "Thêm tài khoản" khỏi bottom-sheet Switcher.
- **Biểu hiện phân mảnh**:
  - TikTok bản cũ: Resource-id khớp `["n72", "lkp", "l9b", "lpw", "l_z", "lrq", "lli"]` -> ném `MACHINE_FULL_8_ACCOUNTS`.
  - TikTok bản mới (v46.x): Resource-id đổi sang `omm`, `omr`, `onj` -> bộ đếm trả về 0, script không thấy nút "Thêm tài khoản" nên ném `Không tìm thấy: ('Thêm tài khoản'...)`.
- **Hành động chuẩn**:
  - Đối chiếu danh sách switcher với Master DAT và `Tik1..7.xlsx`.
  - Nếu nick còn sống và hợp lệ: Backfill vào Row 8 trong Excel theo Invariant Tài sản Farm.
  - Nếu cần reg nick mới: Bắt buộc đăng xuất nick dư ra khỏi app để đưa tổng số nick về 7 trước khi reg.
