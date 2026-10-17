# Sự Cố Lệch Header Cột Folder Video & Bẫy Gán Tuần Tự Trong Đồng Bộ taikhoan_run_safe

## 1. Hiện Tượng & Nguy Cơ Lệch Slot (Incident 2026-10-17)
- **Hiện tượng**: Cronjob nuôi acc TikTok (`feed_session_watchdog`) báo lỗi hàng loạt `profile username still mismatched after switch` ở các phiên chạy theo hàng (ví dụ Row 8 - Ca chiều).
- **Hiện trường điển hình (Máy 76)**:
  - Thiết bị thực tế đang ở tài khoản `@duonghoailan1999` (Folder 608 - tương ứng `Tik8.xlsx`).
  - Tuy nhiên, runner đọc `taikhoan_run_safe.xlsx` yêu cầu tìm nick `@anhhuong5185` (Folder 602 - tương ứng `Tik2.xlsx`), dẫn đến mismatch 100% dù thiết bị và nick đều hoạt động bình thường.

## 2. Nguyên Nhân Gốc Rễ: Header Drift & Fallthrough Tuần Tự
1. **Header Drift trong Master DAT**:
   - Cột Folder Video trong `taikhoan_dat_v2_updated .xlsx` có tiêu đề thực tế là:
     `Folder Video (Slot 1-640)`.
   - Trong `scripts/sync-safe-workbook.py`, hàm `_header_index` chỉ tìm các alias cứng:
     `("folder video", "folder", "thu muc")`.
   - Do header chuẩn hóa thành `'folder video slot 1 640'` không khớp với bất kỳ alias nào, `folder_col` trả về `None`.

2. **Cạm bẫy Fallthrough Gán Slot Tuần Tự**:
   - Khi `folder_col is None`, script không thể tính toán `target_slot = (f_num - 1) % 8`.
   - Logic rơi xuống nhánh fallback gán slot theo thứ tự xuất hiện dòng trong file Excel:
     `slot_idx = next((i for i in range(8) if machine_slots[machine][i] is None), None)`
   - Với các máy có dòng bị thêm sau hoặc xáo trộn trong Master DAT (như M76 dòng Folder 608 nằm ở vị trí thứ 7 và Folder 602 nằm ở vị trí thứ 8):
     - Slot 7 bị gán thành Folder 608 (`duonghoailan1999`).
     - Slot 8 bị gán thành Folder 602 (`anhhuong5185`).
   - Hậu quả: Toàn bộ lịch trình chạy ca Row 8 yêu cầu sai tài khoản trên các máy bị xáo trộn dòng.

## 3. Quy Tắc Khắc Phục & Chuẩn Hóa Bắt Buộc

1. **Bắt buộc hỗ trợ đầy đủ Header Aliases**:
   - Mọi script đọc Master DAT (cả `sync-safe-workbook.py`, `upload_preflight.py`, `ensure_row_accounts.py`) BẮT BUỘC nhận diện:
     ```python
     folder_col = _header_index(
         source_sheet,
         ("folder video slot 1 640", "folder video", "folder", "thu muc", "render dich"),
     )
     ```
2. **Kỷ luật kiểm chứng đối soát 640 Account 1:1 Fleet-wide**:
   - Sau khi đồng bộ `taikhoan_run_safe.xlsx`, BẮT BUỘC chạy script đối soát tự động:
     - Với mỗi máy $m \in [1, 80]$ và slot $s \in [0, 7]$:
       - Account ID trong `taikhoan_run_safe.xlsx` tại dòng $(m - 1) \times 8 + s$ PHẢI khớp 100% với Account ID tại máy $m$ trong file `Tik{s+1}.xlsx`.
     - Tuyệt đối không để xảy ra bất kỳ dòng nào lệch ID (0 discrepancy).

3. **Công thức chuẩn hóa Folder Video & Video Gốc cho Farm Kibe và Admin**:
   - **Kibe (Máy 1–80)**:
     - Folder Video (Render Đích): $F_{vid} = 8 \times (M - 1) + Slot$ (với $Slot \in [1, 8]$).
     - Target Slot: $Slot = ((F_{vid} - 1) \pmod 8) + 1$.
   - **Admin (Máy 201–280)**:
     - Folder Nguồn (Video Gốc): $F_{src} = (Slot - 1) \times 80 + (M - 200)$.
     - Folder Video (Render Đích): $F_{vid} = ((M - 200) - 1) \times 8 + Slot$.
     - Khi kiểm tra `excel_preflight_validator.py`, các file `Tik1..Tik8` của Admin bắt buộc tuân thủ đúng công thức trên (tránh lỗi lệch index 341/363 trên Tik5).
