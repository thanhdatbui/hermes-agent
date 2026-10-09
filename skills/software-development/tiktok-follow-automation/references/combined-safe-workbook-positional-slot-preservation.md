# Combined Safe Workbook Positional Slot Preservation Invariant

## 1. Bối Cảnh Lỗi & Hiện Trường (2026-10-06)
- **Triệu chứng:** Máy 76 (Row 4 `@loanau4423`) có 9 video (>=6) và 42 ngày tuổi (>=21 ngày), đủ điều kiện follow 100%. Tuy nhiên khi chạy follow session, cả Mode 2 và Mode 1 đều không follow được ai, kết thúc sau 84s với `followed: [], followed_count: 0, status: OK`.
- **Nguyên nhân gốc rễ (Root Cause):**
  - Kibe source workbook `D:/OneDrive/TaadaaData/kibe/taikhoan_run_safe.xlsx` có cấu trúc 8 slot cố định cho mỗi máy.
  - Máy 76 có slot Row 2 bị **trống** (chưa có nick):
    - Row 1: `judsoyqo9ng` (9 video)
    - Row 2: *[Ô TRỐNG]*
    - Row 3: `cleorbgtwyr` (9 video)
    - Row 4: `loanau4423` (9 video)
    - Row 5: `ucloan7790` (5 video)
  - Tool gộp workbook `D:/Taadaa/tools/sync_combined_safe_workbook.py` trước đây có logic lọc dồn dòng:
    `if row and len(row) >= 3 and row[2] and str(row[2]).strip():`
    $\rightarrow$ Bỏ qua ô trống ở Row 2, làm toàn bộ các dòng sau đó của Máy 76 bị dồn lên 1 bậc!
  - Trong `taikhoan_run_safe_combined.xlsx`:
    - Row 3: `loanau4423`
    - Row 4: biến thành `ucloan7790` (chỉ có 5 video < ngưỡng 6 video).
  - Khi `multi_machine_feed_session.py` gọi subprocess `run_follow.py --machine 76 --account-row-index 4`:
    - `run_follow.py` đọc file `combined.xlsx`, ánh xạ Row 4 thành `ucloan7790` (5 video).
    - Dual Gate kiểm tra `video_count < 6` $\rightarrow$ Khóa cứng `budget = 0`.
    - Do `budget = 0`, cả Mode 2 (Anchor) lẫn Mode 1 (Search Bù) đều bị chặn đứng không được thực hiện bất kỳ lượt bấm nào.

## 2. Fix đã áp dụng (2026-10-06)
- **File sửa:** `D:/Taadaa/tools/sync_combined_safe_workbook.py`
- **Thay điều kiện lọc:** Từ `if row and ... and row[2] and str(row[2]).strip():` → `if row and len(row) >= 2 and (row[0] is not None or row[1] is not None):` — chỉ bỏ qua hàng hoàn toàn rỗng không có máy/serial; hàng có máy+serial nhưng trống ID vẫn được giữ.
- **Bỏ hẳn `seen_uids` dedup toàn file.**
- **Kết quả:** File combined sau fix có 1.280 dòng, M76 Row 4 đúng là `@loanau4423` (9 video, budget = 3 lượt).
- **Lệnh chạy lại sync:** `python D:/Taadaa/tools/sync_combined_safe_workbook.py` — chạy sau mỗi lần cập nhật workbook nguồn.

## 3. Invariant Bắt Buộc Khi Gộp Safe Workbook (Kibe + Admin)
1. **CẤM TUYỆT ĐỐI lọc bỏ ô trống (Cấm dồn dòng):**
   - Bộ loader `WorkbookMapping` trong `follow_runner.core.workbook.py` tính toán `account_row_index` theo thứ tự xuất hiện các dòng có số máy / device serial.
   - Nếu một slot chưa có nick (ID rỗng), dòng đó **bắt buộc phải được giữ nguyên** trong file combined với `tik_id = ""` để giữ nguyên vị trí index 1..8 cho các slot tiếp theo.
2. **CẤM deduplicate UID trên phạm vi toàn file làm mất dòng:**
   - Mỗi máy trên Farm có ma trận slot vật lý cố định. Việc deduplicate UID giữa các máy hoặc xóa dòng trùng sẽ làm vỡ index của máy đó.
3. **Quy tắc nghiệm thu file Combined Safe Workbook:**
   - Số dòng tối thiểu phải bằng tổng số slot của cả 2 dàn (Kibe 80 máy x 8 slot + Admin 80 máy x 8 slot = 1.280 dòng).
   - Kiểm tra chéo: Row index của bất kỳ máy nào trong file combined (`taikhoan_run_safe_combined.xlsx`) phải trùng khớp 1:1 với row index trong file safe nguồn của dàn đó (`kibe/taikhoan_run_safe.xlsx` hoặc `admin/taikhoan_run_safe.xlsx`).
