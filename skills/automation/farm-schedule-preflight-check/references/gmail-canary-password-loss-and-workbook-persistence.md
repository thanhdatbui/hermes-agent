# Bài Học Vận Hành & Phòng Chống Mất Dữ Liệu Khi Chạy Single Canary Reg Gmail

## 1. Bối cảnh & Hiện tượng lỗi thực tế (12/09/2026)
- Khi chạy thử nghiệm 1 máy thật (Canary Test / Watchdog / Debug thủ công):
  `python D:/Taadaa/register gmail/gmail_reg_v10.py <stt> --ss`
- Quá trình đăng ký trên thiết bị Android diễn ra thành công 100%, tài khoản đăng nhập vào OS Android hoàn tất.
- **SỰ CỐ NGHIÊM TRỌNG:**
  - Script không in mật khẩu ra log console hay file `reg_log.txt` (do cơ chế ẩn pass).
  - Script không ghi tài khoản vào file Excel `gmail_clean_v2.xlsx` vì cơ chế `[WORKBOOK_GUARD] Skip success persistence; use --result-dir and merge step for workbook writes` kích hoạt khi thiếu cờ `--result-dir` (vốn chỉ có trong batch launcher `run_parallel.ps1`).
  - Mật khẩu chỉ nằm trong RAM của tiến trình Python và bị biến mất hoàn toàn khi tiến trình kết thúc.
  - Khi muốn khôi phục hoặc bật 2FA trên thiết bị, Google yêu cầu nhập lại mật khẩu hiện tại; do tài khoản mới chưa có SĐT hay email khôi phục nên không thể reset qua "Forgot password", dẫn đến việc tài khoản bị kẹt trên máy mà không sử dụng được.

---

## 2. Quy tắc Bắt Buộc (Invariants) Khi Chạy Canary / On-Demand

1. **Lưu trữ mật khẩu tức thì (Immediate Password Logging):**
   - Tại thời điểm sinh tài khoản (`generate_account_for_slot`), BẮT BUỘC ghi vết mật khẩu rõ ràng ra log cục bộ (`[ACCOUNT_GEN] Generated {email} | pass: {password}`) để có thể truy vết ngay khi tiến trình gặp sự cố bất ngờ.

2. **Fallback Ghi Trực Tiếp Workbook Nguồn (Direct Workbook Persistence Fallback):**
   - Hàm `persist_success_result(acc)` khi không nhận được `--result-dir` KHÔNG ĐƯỢC PHÉP silently drop (bỏ qua).
   - BẮT BUỘC tích hợp fallback gọi `single_writer_workbook_update` kết hợp `write_success_row` từ `scripts.merge_success_results` để nạp trực tiếp tài khoản vào `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx`.
   - Contract chuẩn:
     ```python
     def _updater(temp_path):
         wb = openpyxl.load_workbook(temp_path)
         try:
             ws = wb.active
             payload = build_success_result_payload(acc)
             payload["stt"] = int(payload["stt"])
             write_success_row(ws, payload)
             wb.save(temp_path)
         finally:
             wb.close()
         return True
     ```

3. **Chống Zombie Summary & Báo Cáo Ma Trong Chained Night Pipeline:**
   - Khi batch hoặc script runner bị crash / NameError ở top-level, hàm phân tích kết quả (`parse_gmail_details`, `parse_tiktok_details`) tuyệt đối CẤM nhặt file summary cũ nhất còn sót lại trong thư mục runtime.
   - BẮT BUỘC kiểm tra `mtime` của summary file: chỉ chấp nhận file tạo trong vòng $\le 3$ giờ (`10800s`). Nếu file cũ hơn $\rightarrow$ coi như rỗng và cảnh báo runner crash thay vì gửi lại kết quả của ngày hôm trước.

4. **Tránh Hardcode Giờ Canh Máy Rảnh (Adaptive Lock Watcher vs Static Timer):**
   - CẤM đoán mò giờ cố định (ví dụ `09:15`) để hẹn giờ chạy máy, vì các phiên nuôi trước đó có thể bị lag, dump XML chậm hoặc kẹt hook khiến lock nhả trễ.
   - BẮT BUỘC dùng cơ chế Watchdog động định kỳ kiểm tra trực tiếp thư mục lock (`~/.codex/device-locks/`), chỉ kích hoạt khi file lock vật lý của máy đã thực sự biến mất và khoảng cách tới ca nuôi kế tiếp $\ge 60$ phút.
