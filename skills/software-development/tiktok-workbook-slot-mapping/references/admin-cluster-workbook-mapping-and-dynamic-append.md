# Quy Tắc Ánh Xạ Slot & Append Động Cho Workbook Cụm Admin (Máy 201–280)

## 1. Phân Biệt Cấu Trúc Workbook Kibe vs Admin
- **Cụm Kibe (Máy 1–80):**
  - Master tracking `taikhoan_dat_v2_updated .xlsx` có cấu trúc lưới cố định gồm đúng 640 dòng (80 máy × 8 slots).
  - Vị trí dòng vật lý: `row = (machine - 1) * 8 + slot + 1`.
  - STT Tik (Cột 2 / Folder Video): `stt_tik = (machine - 1) * 8 + slot`.
- **Cụm Admin (Máy 201–280):**
  - Master tracking `D:/OneDrive/TaadaaData/admin/taikhoan_dat_v2_updated .xlsx` được nạp tài khoản theo dạng **phát triển động (Dynamic Append)**.
  - Mỗi máy ban đầu chỉ có các dòng tương ứng với các slot đã từng có tài khoản (ví dụ: máy 201 có dòng cho slot 1, 2, 3, 7, 8; slot 4, 5, 6 chưa có dòng trong bảng).
  - Công thức STT Tik chuẩn của Admin: `expected_tik = (m - 201) * 8 + slot`.

## 2. Kỹ Thuật Merge Kết Quả Reg Bù (`apply_results` trong `ensure_row_accounts.py`)
Khi quét các file `tracking_result_*.json` sau batch reg để merge vào tracking workbook:
1. **Tìm dòng đích (Target Row Lookup):**
   - Với máy Kibe: tìm `c1 == m` và `c2 in (expected_tik, slot)`. Nếu không thấy, fallback về vị trí lưới `(m - 1) * 8 + slot + 1`.
   - Với máy Admin:
     ```python
     expected_tik = (m - 201) * 8 + slot if m >= 201 else (m - 1) * 8 + slot
     ```
     Quét toàn bộ sheet để tìm dòng khớp máy `m` và slot tương ứng:
     ```python
     if c1 is not None and int(str(c1).strip()) == m:
         if c2 is not None and int(str(c2).strip()) in (expected_tik, slot):
             target_row = r
             break
         if c2 is not None and int(str(c2).strip()) > 0 and ((int(str(c2).strip()) - 1) % 8 + 1) == slot:
             target_row = r
             break
     ```
2. **Dynamic Append Fallback (Bắt Buộc):**
   - Nếu không tìm thấy target row có sẵn trong sheet:
     ```python
     if target_row is None:
         # Với cụm Admin, tự động tạo dòng mới ở cuối sheet thay vì bỏ qua
         target_row = ws_trk.max_row + 1
     ```
   - **Tử huyệt bỏ qua (Silent Drop Pitfall):** Nếu hardcode `if target_row is None: skipped_count += 1; continue;`, toàn bộ các tài khoản reg thành công ở các slot mới của dàn Admin sẽ bị vứt bỏ, workbook không được cập nhật dù nick đã tạo thành công trên máy.
3. **Bảo Toàn Cột 2 (Folder Video / STT Tik):**
   - Giữ nguyên STT Tik cũ nếu dòng đã có giá trị, hoặc gán `expected_tik` (`(m - 201) * 8 + slot`). Tuyệt đối không ghi đè số thứ tự slot trần (`1..8`) vào cột Folder Video làm hỏng mapping render video.
