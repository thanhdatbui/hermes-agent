# Case UI-99: Bảo Toàn Ma Trận Slot Combined Workbook & Giới Hạn Của Pull-To-Refresh Trên Profile (2026-10-06)

## 1. Bối Cảnh & Sự Cố Trôi Lệch Slot (Combined Workbook Drift)
Trong ca chạy Follow ca 4 (Row 4), Máy 76 (M76) hoàn thành với `followed_count = 0` (0 lượt cả Module 2 lẫn Module 1) dù tài khoản `@loanau4423` có 9 video (>= 6) và 42 ngày tuổi (>= 21), hoàn toàn đủ điều kiện Dual Gate.

### Nguyên Nhân Gốc Rễ (Root Cause)
1. **Lỗi Lọc Bỏ Slot Trống Trong `sync_combined_safe_workbook.py`:**
   - Script gộp file an toàn `taikhoan_run_safe_combined.xlsx` từ 2 nguồn Kibe (`taikhoan_run_safe.xlsx`) và Admin (`taikhoan_run_safe.xlsx`) ban đầu có logic lọc:
     ```python
     if row and len(row) >= 3 and row[2] and str(row[2]).strip():
         # Bỏ qua mọi dòng không có ID hợp lệ!
     ```
   - Trên file nguồn Kibe, Máy 76 có slot Row 2 bị trống (chưa có nick/nick chết đã dọn):
     - Slot 1: `judsoyqo9ng` (9 video)
     - Slot 2: *[TRỐNG]*
     - Slot 3: `cleorbgtwyr` (9 video)
     - Slot 4: `loanau4423` (9 video)
     - Slot 5: `ucloan7790` (5 video)
   - Khi script gộp bỏ qua Slot 2 và dồn dòng liên tiếp, toàn bộ chỉ số dòng của Máy 76 bị thụt lùi:
     - Row 1: `judsoyqo9ng`
     - Row 2: `cleorbgtwyr`
     - Row 3: `loanau4423`
     - **Row 4: `ucloan7790` (chỉ có 5 video < 6 video)**
2. **Hệ Quả Dual Gate Khóa Cứng Quota:**
   - Khi Feed session gọi `run_follow.py --machine 76 --account-row-index 4`, runner nạp file `combined.xlsx` và thấy Row 4 có 5 video $\rightarrow$ Dual Gate khóa cứng `budget = 0`.
   - Vì `budget = 0`, cả Module 2 (Anchor) lẫn Module 1 (Search Follow bù) đều bị chặn đứng, trả về 0 lượt sau 84 giây.

### Quy Tắc Bất Biến Về Gộp Workbook (Combined Slot Matrix Invariant)
- **Bảo toàn 100% vị trí Slot:** Khi gộp workbook Kibe và Admin, BẮT BUỘC giữ nguyên từng dòng của từng máy, bao gồm cả các dòng trống (ID rỗng).
- **CẤM TUYỆT ĐỐI dồn dòng hoặc deduplicate UID toàn cục:** Mọi thao tác gộp phải đảm bảo `account_row_index` trong file combined khớp 1:1 tuyệt đối với file nguồn gốc của từng farm.

---

## 2. Giới Hạn Của Thao Tác Pull-To-Refresh Trên Profile TikTok Đối Phương

### Hiện Tượng
Khi M80 chạy Mode 2 follow Anchor 1 (`@allynkapyej`), script xem video $\rightarrow$ bấm follow trên video $\rightarrow$ back ra Profile của Anchor $\rightarrow$ vuốt kéo reload (`pull_to_refresh_profile`) $\rightarrow$ đọc UI thấy nút vẫn là "Đã follow" $\rightarrow$ ghi nhận thành công 1 lượt.  
Tuy nhiên, trên thực tế số `Following` của nick M80 không tăng từ 1 lên 2, và Anchor 1 cũng không tăng `Follower`.

### Nguyên Nhân Kỹ Thuật
1. **Lỗi Vị Trí Vuốt:**
   - Trong `adapter.py::pull_to_refresh_profile`, tọa độ vuốt bắt đầu từ `y = 0.35 * 1920 = 672px` xuống `y = 0.78 * 1920 = 1497px`.
   - Vùng `y >= 600px` trên profile đối phương là danh sách video (`RecyclerView` / `ViewPager`). Kéo từ vị trí này thường bị Android coi là thao tác cuộn video thay vì kéo thanh reload (`SwipeRefreshLayout`).
2. **Cơ Chế Cache Cục Bộ Của App TikTok (Optimistic UI):**
   - App TikTok cache trạng thái nút "Đã follow" sau khi bấm trên video.
   - Khi back về Profile đối phương, app hiển thị trạng thái cache. Thao tác vuốt kéo xuống trên profile của người khác thường chỉ làm nảy nhẹ header (overscroll bounce) chứ không ép server gửi lại payload mới.
3. **Quy Tắc Xác Minh Đích Thực (Path B Standard):**
   - Không được tin cậy thao tác vuốt kéo reload đơn thuần trên profile đối phương.
   - Để kiểm tra chính xác nick có bị nhả không, quy trình chuẩn (như trong `verify_follow.py`) bắt buộc phải: **Back thoát hẳn khỏi màn hình profile $\rightarrow$ Truy cập lại từ đầu (Natural Re-entry qua search hoặc feed)** để ép app fetch lại từ server TikTok.
