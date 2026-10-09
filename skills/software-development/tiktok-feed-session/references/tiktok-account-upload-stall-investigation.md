# Quy trình điều tra tài khoản TikTok ngưng đăng video (Upload Stall Audit)

Khi nhận câu hỏi hoặc alert về việc một tài khoản TikTok nhiều ngày không đăng video mới (ví dụ: "sao nick này hơn 1 tuần rồi không đăng video mới"):

## 6 bước đối soát gốc rễ (Root-Cause Audit Trail)

### Bước 1: Xác định Máy và Slot (Account Mapping)
- Tra cứu `@username` trong `taikhoan_run_safe.xlsx` (Sheet `Accounts`) hoặc bảng `account_mapping` trong `D:/Taadaa/data/tiktok_tracker.db`.
- Xác định:
  - Máy ($M \in [1..80]$) và Device Serial.
  - Vị trí Slot ($Row \in [1..8]$) trên máy đó.

### Bước 2: Đối soát Tik Workbook & Thư mục Video (Folder Mapping)
- Quy tắc mapping: Slot index $Row$ tương ứng với file `Tik<Row>.xlsx` trong `D:\OneDrive\TaadaaData\kibe\`:
  - Slot 1 -> `Tik1.xlsx`
  - Slot 2 -> `Tik2.xlsx`
  - Slot 3 -> `tik3.xlsx`
  - Slot 4 -> `Tik4.xlsx`
  - Slot 5 -> `Tik5.xlsx`
  - Slot 6 -> `Tik6.xlsx`
  - Slot 7 -> `Tik7.xlsx`
  - Slot 8 -> `Tik8.xlsx`
- Mở dòng tương ứng với Máy $M$ trong file `Tik<Row>.xlsx` để đọc:
  - `folder_video`: ID thư mục video render (ví dụ: `261`).
  - `video gốc`: ID folder gốc.
  - `posted_count`: Số video đã đăng ghi nhận trong workbook.

### Bước 3: Kiểm tra kho video render (Media Readiness)
- Video kế tiếp cần upload là: `D:\TIKTOK-videonuoinick\<folder_video>\<posted_count + 1>.mp4`.
- Kiểm tra:
  - File có tồn tại không?
  - Dung lượng file > 0 bytes không?
- **Nguyên nhân phổ biến 1:** Cạn kho video (hết clip render sẵn hoặc batch render chưa chạy tới folder này).

### Bước 4: Kiểm tra các Cổng chặn trong Upload Preflight (`_run_upload_hook`)
Trong `python_runner/flows/multi_machine_feed_session.py`:
1. **Gate 1 - Session Index:** Chỉ session cuối cùng trong ca (`session_index == 2` hoặc `_allow_upload_hook`) mới kích hoạt upload hook.
2. **Gate 2/3 - Stop Reason:** Nếu feed session dừng do lỗi nhạy cảm (`sensitive-skip`), upload bị bỏ qua.
3. **Gate 4c - Cooldown Eligibility:** 
   - Với Tik 5, Tik 6+: Phải qua mốc `BENCHMARK_MIN_UPLOAD_DATE` (2026-09-11) và đủ 3 ngày tuổi từ ngày tạo (`taikhoan_dat_v2_updated .xlsx`).
4. **Organic Rest Day (Ngày nghỉ dưỡng sinh):** 
   - Tỷ lệ nghỉ 1/3 (Dưỡng sinh = 0 Follow + 0 Upload) để tránh spam ban, trừ khi nick được gắn cờ cắn đề xuất (`BOOST` / `is_account_boosted`).

### Bước 5: Kiểm tra Lịch trình Ca & Lịch sử Upload thực tế
- Lịch phân bổ Ca theo Row:
  - Ca 1 (Sáng 06:00 - 12:00): Row 1 & Row 2
  - Ca 2 (Trưa 12:00 - 18:00): Row 3 & Row 4
  - Ca 3 (Tối 18:00 - 00:00): Row 5 & Row 6
  - Ca 4 (Đêm 00:00 - 06:00): Row 7 & Row 8
- Kiểm tra file ledger: `C:\ProgramData\Taadaa\tiktok-upload-concurrency-v1\shift_upload_history.json`.
- Kiểm tra `D:\Taadaa\runtime\kibe\cron-state\post_state.json`.
- Xác định xem trong tuần qua, Ca tương ứng có được chạy đầy đủ trên Máy $M$ hay máy bị mất kết nối ADB, kẹt lock, hoặc bị lỗi proxy.

### Bước 6: Trích xuất Snapshot Timeline
- Truy vấn SQLite `D:/Taadaa/data/tiktok_tracker.db` bảng `snapshots` theo `username`:
  - Kiểm tra tiến trình tăng trưởng follower, like, và số video qua từng ngày để xác định chính xác ngày upload thành công gần nhất.
