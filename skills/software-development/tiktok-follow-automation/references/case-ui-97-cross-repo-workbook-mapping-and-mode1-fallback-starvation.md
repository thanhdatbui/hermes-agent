# Case UI-97: Lệch Mapping Workbook Giữa Các Repo Dẫn Tới Đói Budget & Triệt Tiêu Fallback Mode 1 (2026-10-06)

## 1. Bối Cảnh & Hiện Tượng
- **Thắc mắc của User:**
  > *"module 2 k khớp thì phải chạy module 1 chứ làm sao có chuyện k follow đc ai????"*
- **Hiện tượng trên máy M76 (Row 4):**
  - Trong session lướt feed: Chạy nick `@loanau4423` (9 video, 42 ngày tuổi) thành công, bấm follow tự nhiên 3 video.
  - Khi follow-hook (`run_follow.py`) chạy trong 84 giây:
    - `mode2_followed_count: 0`
    - `mode1_followed_count: 0`
    - `followed: []`, exit_code: 0, status: `OK`.
  - Không có bất kỳ tài khoản nào được follow dù Mode 1 được thiết kế tự động bù khi Mode 2 cạn anchor.

## 2. Phân Tích Nguyên Nhân Gốc (Root Cause)
1. **Lệch cấu hình nguồn Workbook:**
   - Feed runner (`multi_machine_feed_session.py`) đọc workbook chuẩn của cụm:
     `D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx`.
     Tại file này, Máy 76 Row 4 = `@loanau4423` (9 video, 42 ngày tuổi).
   - Khi Feed runner gọi lệnh follow-hook:
     `python -m follow_runner.run_follow --machine 76 --account-row-index 4 --skip-identity-verify`
     Lệnh **KHÔNG truyền cờ `--workbook` / `--account-workbook`**, nên `run_follow.py` nạp từ file cấu hình mặc định `config.example.yaml`.
   - File `config.example.yaml` lại trỏ cứng vào:
     `D:\OneDrive\TaadaaData\taikhoan_run_safe_combined.xlsx`.
2. **Lệch chỉ số dòng (Row Index Shift):**
   - File `taikhoan_run_safe_combined.xlsx` đã bị lược bỏ các dòng trống (Máy 76 bị trống Row 2 trong file chuẩn).
   - Khi lược bỏ Row 2, toàn bộ các row phía sau bị đôn lên 1 bậc trong file `combined`:
     - Row 3: `@loanau4423` (9 video)
     - **Row 4:** `@ucloan7790` (**5 video** - `video_count = 5 < 6`)!
3. **Triệt tiêu Budget từ Dual Gate:**
   - Khi `run_follow.py` phân giải Row 4 từ file `combined`, nó nhận diện nick là `@ucloan7790` với `video_count = 5`.
   - Dual Gate (`follow_state.py`) kiểm tra: `if video_count < 6:` $\rightarrow$ **Cấp `session_budget = 0`**.
   - Khi budget = 0:
     - Mode 2 kiểm tra `used >= budget (0 >= 0)` $\rightarrow$ Dừng ngay, follow 0 nick.
     - Mode 1 kiểm tra `used >= budget (0 >= 0)` $\rightarrow$ Dừng ngay, follow 0 nick.
   - Kết quả trả về `status: OK, followed: []` tạo cảm giác Mode 1 không chạy bù.

## 3. Bài Học & Giải Pháp Kiến Trúc
1. **Bắt buộc truyền explicit `--workbook` khi gọi cross-repo runner:**
   - Trong `multi_machine_feed_session.py`, lệnh spawn `run_follow.py` bắt buộc phải kèm cờ workbook chỉ định rõ path từ cụm runtime (`account_workbook` của cluster), không để subprocess tự resolve sang file `combined` cũ.
2. **Nguyên tắc đồng bộ Row Mapping:**
   - Mọi workbook nạp cho runner phải giữ nguyên cấu trúc 8 slot cố định trên mỗi máy (kể cả ô trống None), tuyệt đối không compact/xóa hàng trống làm lệch mapping 1-based `account_row_index`.
