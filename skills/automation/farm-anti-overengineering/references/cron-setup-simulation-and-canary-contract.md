# Cron Setup Simulation & Real Canary Verification Contract

## 1. Context & Root Cause
- **Vấn đề đã xảy ra:** Cron setup/fix xong chỉ chạy cờ `--dry-run` hoặc mock payload để nghiệm thu, dẫn đến:
  1. Mock script trả về kết quả giả lập (ví dụ hardcoded `SUCCESS=40`), che giấu hoàn toàn các lỗi thực thi runtime thật (sai path, sai tham số CLI `--all-online`, lỗi import, lệch file cấu hình).
  2. Đến đúng giờ cron kích hoạt thật vào ngày hôm sau mới phát hiện lỗi gãy chuỗi (Code 1 / Code 2), làm tê liệt luồng tự động hóa cả ngày của farm.
  3. Lỗi ô nhiễm `sys.path` / `cwd`: Khi cron chạy từ thư mục user home (`C:\Users\Kibe`), Python ưu tiên load các file script rác trùng tên nằm tại thư mục đó thay vì repo chính, gây `AttributeError` khi nạp functions.

## 2. Invariant Rules Khi Setup / Fix Cron
1. **CẤM TUYỆT ĐỐI nghiệm thu bằng mock / dry-run thuần túy:**
   - Cờ `--dry-run` chỉ dùng để kiểm tra syntax parser của chính cron wrapper.
   - Không được coi `--dry-run` là bằng chứng nghiệm thu hoạt động của chuỗi runner bên dưới.
2. **BẮT BUỘC Canary thực chiến (1-2 máy rảnh):**
   - Mọi thay đổi logic gọi lệnh, launcher batch hoặc cron script BẮT BUỘC phải thực hiện chạy thử live trên ít nhất 1-2 máy thật đang rảnh (hoặc probe trực tiếp subprocess thật của runner với `--rows <N>` / single-target) ngay trong phiên.
   - Phải xác nhận tiến trình thật khởi động, nạp đúng interpreter, đọc đúng `cwd` và parse đúng CLI options.
3. **Cô lập CWD (Working Directory) cho Subprocess:**
   - Trong mọi runner script/watchdog khi gọi `subprocess.run` / `Popen` các tool nghiệp vụ, BẮT BUỘC truyền rõ `cwd=str(REPO_DIR)`.
   - Tránh để mặc định rơi vào `C:\Users\Kibe` gây import nhầm file rác.
4. **Quy chuẩn Report cho Cron (Kibe & Admin dùng chung):**
   - Mọi cron watchdog sau khi chạy xong BẮT BUỘC xuất report rõ ràng về các kênh thông báo đã cấu hình.
   - Cron kịch bản dùng chung qua Master Deploy, tự động tách biệt dữ liệu theo `TAADAA_HOST_CONFIG`.
