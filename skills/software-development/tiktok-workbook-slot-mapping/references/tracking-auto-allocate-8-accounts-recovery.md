# PITFALL: Lỗi Khuyết Dòng Khi Máy Chưa Đủ 8 Hàng và Cơ Chế Tự Động Cấp Slot Tracking

## 1. Triệu chứng & Bẫy Suy Diễn Sai Lầm
- **Hiện tượng:** Khi chạy batch `_run_all_targets.py` hoặc `social_reg_v1.py`, script báo lỗi:
  `[07] Tat ca N email cua STT ... da co TK TikTok`.
- **Bẫy suy diễn sai:** Vội vàng cho rằng "bên bán mail đã tạo tài khoản / resell".
- **Thực tế kỹ thuật:** Chính các batch reg trước đó của Farm đã tạo tài khoản thành công nhưng bị kẹt ở tầng ghi nhận dữ liệu!

## 2. Cơ chế lỗi kỹ thuật
1. Trong batch run, script con lưu kết quả reg thành công dưới dạng JSON hoãn ghi (`tracking_result_stt<stt>_<email>.json`) tại `D:/Taadaa/runtime/admin/artifacts/runs/social-batch-all/<batch_run>/...`.
2. Khi tiến trình cha chạy `write_deferred_results_sequential()`, hàm `resolve_tracking_slot()` trước đây chỉ tìm dòng trống có sẵn của STT đó. Nếu máy đã có 4-6 tài khoản (đầy các dòng khởi tạo ban đầu), hàm fail với lỗi `BLOCKED_DATA_CONFLICT (NO_EMPTY_TRACKING_SLOT)`.
3. Nick đã reg thành công trên app TikTok nhưng KHÔNG được ghi vào file Master `taikhoan_dat_v2_updated .xlsx`.
4. Lần chạy tiếp theo, bộ lọc `_detect_clean.py` đọc file Excel thấy email chưa có username nên tiếp tục bốc ra để reg. Khi gõ vào TikTok, TikTok nhận diện đã có tài khoản và chuyển sang màn OTP/Password, dẫn đến lỗi lặp lại.

## 3. Giải pháp kỹ thuật chuẩn hóa (2026-09-27)
- **Tự động cấp slot mới (Auto-allocate slot):**
  - Trong `scripts/deferred_tracking_writer.py`, hàm `_allocate_tracking_row(ws, stt, machine_rows)` được kích hoạt khi máy có `< 8 accounts` (`MAX_TRACKING_ACCOUNTS_PER_MACHINE = 8`).
  - Hàm tự động append dòng mới vào workbook, xác định `Tik` kế tiếp (slot 1..8 hoặc max+1 cho legacy Tik values), copy font/border/fill/number_format từ dòng trước đó qua public attributes (tránh truy cập private `_style`).
  - Không bao giờ ghi đè lên dòng đã có `existing_id` hoặc `existing_pass`.

## 4. Quy trình đối soát & Thu hồi khi nghi ngờ tài khoản reg bị kẹt JSON
```bash
python scripts/recover_deferred_93_accounts.py --tracking "D:/OneDrive/TaadaaData/admin/taikhoan_dat_v2_updated .xlsx" --artifacts "D:/Taadaa/runtime/admin/artifacts/runs/social-batch-all"
```
- Script tự động:
  1. Tạo backup an toàn trong `recovery-backups/`.
  2. Gom các `tracking_result_*.json` có status `SUCCESS` mới nhất.
  3. Lọc ra các email chưa có trong file Excel.
  4. Ghi nối tiếp vào workbook và xác thực sau khi lưu.
