# C2 == Slot Trap & Deferred Merge Reconcile (2026-09-17)

## 1. Triệu chứng sự cố
- Trong ca chạy Ca 4 ngày lẻ (Row 7), hệ thống kích hoạt reg bù tự động qua `ensure_row_accounts.py 7`.
- Batch 1 (00:08) và Batch 2 (01:32) đăng ký thành công tổng cộng **28 tài khoản** (sinh đầy đủ file `tracking_result_*.json` trạng thái `SUCCESS`).
- Tuy nhiên, sau khi script kết thúc và sync sang `taikhoan_run_safe.xlsx`, toàn bộ 28 máy này ở Row 7 vẫn hiển thị `None` (0/28 acc được nạp).

## 2. Nguyên nhân gốc rễ (Root Cause)
1. Trong file master `taikhoan_dat_v2_updated .xlsx`:
   - Cột A (`c1`) là `STT_May` (1..80).
   - Cột B (`c2`) là `STT_Tik` / `Folder Video` toàn cục (1..640), được đánh số liên tục 8 dòng/máy (ví dụ Máy 1 là 1..8; Máy 2 là 9..16; Máy 13 là 97..104).
2. Hàm `apply_results()` trong `ensure_row_accounts.py` lại kiểm tra điều kiện:
   ```python
   if c1 is not None and int(str(c1).strip()) == m:
       if c2 is not None and int(str(c2).strip()) == slot:
           target_row = r
           break
   ```
   Với `slot = 7`:
   - Chỉ duy nhất Máy 1 có `c2 == 7` thỏa mãn.
   - Toàn bộ các máy từ M02 đến M80 đều có `c2 != 7` (ví dụ M13 có `c2` từ 97 đến 104).
3. Do không tìm thấy `target_row`, script kích hoạt fallback dòng trống và **append 28 acc này xuống tận đáy sheet (từ dòng 642 đến 669)**.
4. Script `sync-safe-workbook.py` khi build `taikhoan_run_safe.xlsx` chỉ lấy đúng 8 dòng đầu của từng máy (`entries[:8]`), nên 28 acc bị đẩy ở đáy file bị loại bỏ hoàn toàn.

## 3. Quy tắc chuẩn hóa & Khắc phục
1. **Công thức định vị dòng vật lý tuyệt đối**:
   $$\text{target\_row} = 1 + (m - 1) \times 8 + k$$
   (với $m$ là số máy $1..80$, và $k$ là Slot/Row $1..8$).
2. **CẤM so sánh Cột B với Slot**: Cột B là `Folder Video` / `STT_Tik` toàn cục, không phản ánh chỉ số slot $1..8$.
3. **BẢO TOÀN CỘT 2 (STT TIK / FOLDER VIDEO)**: Khi nạp dữ liệu vào `target_row`, TUYỆT ĐỐI KHÔNG ghi đè Cột 2 thành `slot` (ví dụ 7). Bắt buộc giữ nguyên giá trị cũ của `ws_trk.cell(target_row, 2).value` nếu có, hoặc fallback `(m - 1) * 8 + slot`.
4. **Quy trình Reconcile 28 acc**:
   - Chuyển dữ liệu 28 dòng bị append nhầm (dòng 642..669) vào đúng dòng Slot 7 (`1 + (m-1)*8 + 7`) của 28 máy tương ứng (giữ nguyên STT Tik ở Cột 2).
   - Xóa sạch các dòng dư ở đáy file master: `ws.delete_rows(642, ws.max_row - 641)`.
   - Chạy `python "D:/Taadaa/tiktok-luot nuoi acc/scripts/sync-safe-workbook.py"` để cập nhật `taikhoan_run_safe.xlsx`. Nghiệm thu số lượng acc Row 7 tăng đủ 63 acc.
