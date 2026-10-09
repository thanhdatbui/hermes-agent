# Quy Chuẩn Lưu Trữ Dữ Liệu & Excel Cho Quy Trình Register Gmail (2026-09-04)

## 1. Cơ Chế Lưu Trữ (Workbook Persistence Architecture)

Trong repo `D:\Taadaa\register gmail`, cơ chế ghi trực tiếp vào file Excel (`write_excel_result`) đã bị vô hiệu hóa hoàn toàn (`ALLOW_WORKBOOK_WRITES = False`, `WORKBOOK_GUARD`) nhằm chống tranh chấp file (file lock collision / race conditions) khi nhiều máy chạy song song:

- **Khi chạy Test Canary / Thủ công 1 máy (`python gmail_reg_v10.py <M> --ss`):**
  - Không truyền `--result-dir` $\rightarrow$ `WORKBOOK_GUARD` tự động bỏ qua bước ghi Excel.
  - Trạng thái thành công chỉ lưu trên thiết bị Android (`dumpsys account` / Gmail app) và ghi log tại `C:\Users\Kibe\AppData\Local\register-gmail\reg_log.txt`.
  - **Lưu ý:** Muốn nạp tài khoản test vào Excel thì cần chạy merge thủ công hoặc truyền `--result-dir`.

- **Khi chạy Batch Tự Động (`run_all.ps1` / `run_night_chain_pipeline.py`):**
  - `run_parallel.ps1` tự động tạo thư mục `$resultDir = <logDir>\results` và truyền `--result-dir "$resultDir"` cho từng worker.
  - Mỗi worker khi thành công sẽ tạo file payload `machine_<STT>.success.json` chứa: `stt`, `email`, `password`, `ngay_sinh`, `dob`, `ngay_tao`, `username`, `profile`.
  - Sau khi toàn bộ các máy chạy xong, script gọi `scripts\merge_success_results.py` để thực hiện **Single-Writer Update** hợp nhất toàn bộ kết quả vào file Excel nguồn duy nhất.

---

## 2. Phân Định Các File Excel / Output Đích

1. **`D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx` (File nguồn Mail chính của Farm):**
   - **Mục đích:** Lưu trữ toàn bộ Gmail/Hotmail live đã đăng nhập thực tế trên các máy điện thoại của dàn Kibe (Máy 1 - 80).
   - **Cấu trúc cột:** `số máy` (1), `tài khoản gmail` (2), `pass mail` (3), `2fa` (4), `mail khôi phục` (5), `ngày tháng năm sinh` (6), `ngày tạo` (7), `mã phục hồi` (8), `token` (9), `client_id` (10), `trạng thái` (11).
   - **Quy tắc:** Chỉ ghi nhận tài khoản đã login live trên máy. Hotmail mới mua hoặc chưa login máy tuyệt đối không đưa vào file này.

2. **`D:\OneDrive\TaadaaData\kibe\master_gmail_manager.xlsx` (File Quản Lý Master Gmail):**
   - **Mục đích:** Bảng tổng hợp đối soát cấp cao (Master view) quản lý trạng thái LIVE/DIE, Device ID serial, Model điện thoại, Proxy gán và profile GPM.

3. **`D:\OneDrive\TaadaaData\kibe\taikhoan_dat_v2_updated .xlsx` (Bảng Tracking TikTok Farm):**
   - **Mục đích:** Quản lý toàn bộ 6 slot tài khoản TikTok của 80 máy farm.
   - **Quy tắc:** Mail chỉ được nạp sang file này sau khi Phase 2 (`Tiktok_Reg`) dùng mail đó đăng ký thành công tài khoản TikTok.
