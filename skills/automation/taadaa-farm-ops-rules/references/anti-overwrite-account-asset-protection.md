# Quy Tắc Bảo Toàn Tài Sản Nick & Chống Ghi Đè Excel Tracking

## 1. TÀI SẢN NICK CỦA USER LÀ BẤT KHẢ XÂM PHẠM
- Mọi nick đã đăng ký hoặc đang nằm trên máy đều là tài sản thực tế của user.
- TUYỆT ĐỐI CẤM coi là rác, CẤM tự ý xoá, CẤM ghi đè thông tin nick mới lên hàng chứa nick cũ.

## 2. BẢO VỆ CẤU TRÚC LƯỚI EXCEL TRACKING (`taikhoan_dat_v2_updated .xlsx`)
- Cấu trúc: Mỗi máy sở hữu đúng 8 dòng vật lý tương ứng 8 Folder Video (1 đến 8).
- CẤM TUYỆT ĐỐI dùng `sheet.delete_rows()` hoặc `sheet.insert_rows()` làm xô lệch index và drift mapping.
- Vị trí hàng vật lý = `(Máy - 1) * 8 + Slot + 1`.

## 3. NGUYÊN TẮC GHI TRACKING (`NEVER_OVERWRITE_GUARD`)
- Trước khi ghi nick mới vào bất kỳ hàng nào, BẮT BUỘC kiểm tra:
  - Nếu ô đã có `ID`, `PASS`, hoặc `GMAIL` khác với email vừa reg -> CẤM GHI ĐÈ!
  - Bắt buộc quét tìm hàng trống tiếp theo của máy đó (hàng có cả ID, PASS, GMAIL đều rỗng).
- Nếu máy đã đủ 8 nick -> BẮT BUỘC STOP & FAIL-CLOSED với mã lỗi `MACHINE_FULL_8_ACCOUNTS` / `REJECT_OVERWRITE_MACHINE_ALREADY_FULL`. Không được cố nhồi nhét hay ghi đè.

## 4. QUY TRÌNH PHỤC HỒI NICK BỊ GHI ĐÈ
- Khi phát hiện nick cũ bị mất hoặc ghi đè:
  1. Sao lưu ngay file hiện tại (`_BEFORE_RESTORE_*.xlsx`).
  2. Truy lục các bản backup cũ trong `workbook-backups` hoặc `.bak_final.xlsx` để lấy lại 100% metadata gốc: ID, Pass TT, 2FA, Email, Pass mail, DOB, Created Date.
  3. Trả nick cũ về đúng hàng/Folder gốc của nó.
  4. Di dời nick mới reg xuống các hàng/slot còn trống của máy.
