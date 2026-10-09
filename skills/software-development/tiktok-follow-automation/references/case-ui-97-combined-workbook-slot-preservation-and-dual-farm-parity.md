# Case UI-97: Bảo Toàn Ma Trận Slot 8 Hàng Cho Workbook Combined & Quy Tắc Khấu Trừ Follow Tự Nhiên Theo Phát Chéo Đầu (2026-10-06)

## 1. Sự Cố Lệch Row Ma Trận Trong Workbook Combined (`taikhoan_run_safe_combined.xlsx`)
- **Triệu chứng:** Máy 76 Row 4 (`@loanau4423`, 9 video, 42 ngày tuổi) khi chạy follow hook lại kết thúc với `followed: 0, status: OK`, hoàn toàn không follow ai dù cả Module 2 lẫn Module 1 đều có sẵn trong cấu hình.
- **Root Cause:**
  - `sync_combined_safe_workbook.py` khi gộp từ `kibe/taikhoan_run_safe.xlsx` và `admin/taikhoan_run_safe.xlsx` đã dùng điều kiện:
    `if row and len(row) >= 3 and row[2] and str(row[2]).strip():`
  - Điều này đã **lọc bỏ toàn bộ các dòng trống** (các slot chưa reg nick hoặc nick chết đã dọn).
  - Máy 76 vốn có Slot Row 2 trống $\rightarrow$ Việc bỏ dòng trống làm toàn bộ các slot sau bị **thụt lùi 1 bậc**:
    - Slot 3 (`@cleorbgtwyr`, 9 video) thành Index 2
    - Slot 4 (`@loanau4423`, 9 video) thành Index 3
    - **Slot 5 (`@ucloan7790`, 5 video) thành Index 4!**
  - Khi runner gọi `run_follow.py --machine 76 --account-row-index 4`, runner đọc file `combined.xlsx` và thấy Row 4 có 5 video (< 6 video) $\rightarrow$ Dual Gate khóa cứng `budget = 0`.
  - Hậu quả: Cả Module 2 lẫn Module 1 đều bị ngắt ngay lập tức, không thực thi bất kỳ lượt follow nào.

## 2. Invariant: Bảo Toàn Ma Trận 8 Slot/Máy Cho File Combined
1. **Cấm dồn dòng khi gộp workbook:**
   - File `taikhoan_run_safe_combined.xlsx` phục vụ cho pool follow chéo giữa 2 farm (Kibe 1-80 + Admin 201-280).
   - Mỗi máy bắt buộc phải bảo toàn đúng cấu trúc 8 slot (Row 1 đến Row 8).
   - Slot nào chưa có nick thì giữ nguyên ô ID trống (None / ""), tuyệt đối **không được drop dòng trống** làm xô lệch `account_row_index`.

## 3. Quy Tắc Đối Soát & Khấu Trừ Follow Tự Nhiên Theo Phát Chéo Đầu (User Chốt 2026-10-06)
- **Quy tắc phát đầu tiên:**
  - **Nhả ngay phát đầu (`cnt == 0` & `FOLLOW_FAILED`):** Chứng tỏ nick đã bị TikTok chặn/nhả từ trước khi vào phiên $\rightarrow$ Toàn bộ follow tự nhiên bấm lúc lướt feed trước đó đều vô hiệu $\rightarrow$ **Trừ sạch 100% follow tự nhiên**.
  - **Phát đầu thành công (`cnt > 0`):** Chứng tỏ tại thời điểm lướt feed nick hoàn toàn bình thường $\rightarrow$ **Follow tự nhiên được ghi nhận hợp lệ**.
- **Xử lý đối soát TikTok Web cuối phiên:**
  - Khi một nick kết thúc với `FOLLOW_FAILED` (bị nhả sau vuốt / anchor drop), TikTok server thường không commit hoặc rollback các lượt follow trên server.
  - Watchdog ghi nhận hành vi thực thi trên máy, nhưng trong bảng Đối soát TikTok Web phải nhận biết trạng thái `FOLLOW_FAILED` để không so sánh cứng tạo ra cảnh báo lệch âm vô lý (`Lệch -2`).
