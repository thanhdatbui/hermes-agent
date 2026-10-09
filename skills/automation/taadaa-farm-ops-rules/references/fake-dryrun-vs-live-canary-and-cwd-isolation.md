# Pitfall: Fake Dry-Run vs Real Invocation & CWD Path Poisoning

## 1. "Giả Lập Đến Giờ Chạy" = Live Simulation, KHÔNG ĐƯỢC Mock Dry-Run
- **Triệu chứng:** Người dùng yêu cầu *"chạy canary giả lập đến giờ chạy xem còn lỗi không"*, agent thêm cờ `--dry-run` vào runner, trong khi code `--dry-run` chỉ là nhánh hardcode trả về string `"TOTAL=40 SUCCESS=40 (dry-run)"`.
- **Hậu quả:** Báo cáo thành công giả tạo (fake success), không hề thực thi qua subprocess gọi PowerShell / Python runner thật. Khi đến giờ chạy thật, các lỗi cú pháp CLI, lỗi cwd, thiếu module hay xung đột mapping mới bung ra làm crash toàn bộ đàn.
- **Kỷ luật:**
  1. Khi được bảo *"giả lập / canary đến giờ chạy"*: BẮT BUỘC phải kích hoạt luồng thực tế (real execution path). Nếu cần giới hạn tải, chạy canary 1 máy (`--limit 1` hoặc `--rows <row>`) hoặc kiểm tra từng pipeline con ở chế độ live. CẤM TUYỆT ĐỐI tin vào các cờ `--dry-run` trả về mock data rỗng.
  2. Bắt buộc kiểm tra code của hàm `--dry-run` trước khi dùng: nếu nó chỉ `return 0, "mock string"` thì việc chạy `--dry-run` là hoàn toàn vô giá trị.

## 2. Subprocess Gọi Script Ngoài Phải Luôn Truyền Explicit `cwd`
- **Triệu chứng:** Subprocess chạy PowerShell/Python từ cron wrapper nhưng không đặt `cwd=str(REPO_DIR)` mà để mặc định kế thừa `cwd` của tiến trình gọi (ví dụ `C:\Users\Kibe`).
- **Hậu quả:**
  - Python tự động đưa thư mục hiện tại (`C:\Users\Kibe`) vào vị trí đầu tiên của `sys.path`.
  - Nếu trong `C:\Users\Kibe` có file rác trùng tên (ví dụ `gmail_reg_v10.py` bản nháp cũ), Python sẽ load nhầm file này thay vì file thật trong `D:\Taadaa\register gmail\`.
  - Gây ra lỗi kỳ quặc: `AttributeError: module 'gmail_reg_v10' has no attribute 'load_device_map_from_excel'`.
- **Kỷ luật:** Mọi lệnh `subprocess.run` / `Popen` gọi script con thuộc repo khác BẮT BUỘC phải truyền `cwd=str(REPO_DIR)` rõ ràng.
