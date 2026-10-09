# Điều tra Thiết Bị Offline, Lệch Serial & Cạm Bẫy Phục Hồi Nick Cũ

Tài liệu ghi lại quy trình chuẩn và các cạm bẫy thực chiến khi điều tra thiết bị Android trên Phone Farm Taadaa khi gặp lệnh kiểm tra/điều khiển máy, phát hiện nick DIE hoặc mất kết nối ADB.

---

## 1. Hiện Tượng & Cạm Bẫy Lệch Serial (Serial Drift / Desync)

### Hiện tượng
Khi chạy kiểm tra $O(1)$ qua `inspect_machine.py <N>`, script báo:
```text
[MÁY N] (Kibe Local | Serial: <serial_A>)
• Model: adb.exe: device '<serial_A>' not found
```
Tuy nhiên, kiểm tra file tracking (`taikhoan_dat_v2_updated .xlsx` hoặc `taikhoan_run_safe.xlsx`) lại thấy ghi nhận một serial khác (`<serial_B>`).

### Nguyên nhân gốc rễ
- `inspect_machine.py` đọc serial từ file cấu hình proxy (`PROXYgandienthoai.xlsx`).
- Khi farm có sự tráo máy, đổi hub hoặc sửa file không đồng bộ, serial trong `PROXYgandienthoai.xlsx` và `taikhoan_dat_v2_updated .xlsx` có thể bị lệch nhau (ví dụ: Máy 30 từng bị lệch giữa `ce0416040cba423104` và `ce0217126cd4bc640c`).

### Quy trình đối soát chéo chuẩn:
1. Đọc serial từ cả 2 nguồn: `PROXYgandienthoai.xlsx` và `taikhoan_dat_v2_updated .xlsx`.
2. Chạy `adb devices` để lấy danh sách serial thực tế đang cắm trên máy tính.
3. So sánh:
   - Nếu serial nằm trong `adb devices` nhưng sai máy: cần chỉnh lại mapping trong file Excel tương ứng.
   - Nếu cả 2 serial đều không có trong `adb devices`: máy chắc chắn đang bị mất kết nối phần cứng (lỏng cáp USB, tắt nguồn, treo hub).

---

## 2. Quy Trình 3 Bước Xử Lý Khi Nhận Lệnh Điều Khiển Máy Offline

Khi user phát lệnh: *"Điều khiển máy N mở nick đó ra kiểm tra"*:
1. **Bước 1 (Inspect O(1)):** Chạy `python D:/Taadaa/tools/inspect_machine.py <N>`.
2. **Bước 2 (Kiểm tra liveness ADB):** Nếu báo `device not found`, chạy `adb devices` để rà soát toàn bộ cụm. Thống kê rõ ràng: bao nhiêu máy đang online, máy nào đang offline.
3. **Bước 3 (Báo cáo thực tế & Dừng an toàn):** CẤM TUYỆT ĐỐI spam các lệnh `adb shell input` vào serial không tồn tại. Báo cáo ngay cho user:
   - Tình trạng offline của máy (mất kết nối ADB/cáp).
   - Hướng dẫn user kiểm tra phần cứng (cáp cắm, hub, nguồn máy).

---

## 3. Cạm Bẫy Phục Hồi Nick Cũ Từ Backup Cũ (Stale Account Backfill)

### Hiện tượng
Sau khi khôi phục nick từ các bản sao lưu Excel cũ (hơn 1–2 tháng trước) để lấp vào các slot trống (ví dụ: Slot 8 / Folder 240 của Máy 30), nick lập tức bị báo `NOT_FOUND` hoặc `DIE` trên Dashboard và Cronjob tracker.

### Nguyên nhân
- Nick từ backup cũ (ví dụ: đợt tháng 7) lâu ngày không hoạt động, không có video hoặc chưa hoàn tất verify có thể đã bị TikTok quét dọn / xóa khỏi hệ thống.
- Khi kiểm tra endpoint công khai: `https://www.tiktok.com/@<username>`, TikTok trả về:
  ```json
  {"statusCode": 10221, "statusMsg": "", "userInfo": null}
  ```
  Xác nhận profile không còn tồn tại trên server TikTok.

### Quy tắc phòng ngừa:
- **Pre-check Live trước khi backfill:** Trước khi ghi nick từ backup cũ vào Excel tracking, nên dùng request kiểm tra nhanh profile công khai trên web xem có trả về `userInfo` hợp lệ không.
- **Ưu tiên Reg mới:** Với các slot trống lâu ngày, giải pháp bền vững và an toàn nhất cho farm là đưa vào luồng đăng ký mới (`Tiktok_Reg`) thay vì tái sử dụng nick rác/nick chết từ backup cũ.
