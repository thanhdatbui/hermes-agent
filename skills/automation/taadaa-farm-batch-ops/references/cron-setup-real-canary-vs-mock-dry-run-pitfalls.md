# Quy Chuẩn Nghiệm Thu Setup/Sửa Cron: Cấm Bẫy Dry-Run/Mock và Bắt Buộc Chạy Thật Giả Lập

## Bối cảnh thực tế (Sự cố Chuỗi Sau Ca Trưa 13/09/2026)
Khi setup hoặc sửa chữa cron job farm (chuỗi Reg Gmail -> Add 2FA TikTok):
- **Bẫy dry-run / mock**: Script cron có cờ `--dry-run` trả về chuỗi hardcode `TOTAL=40 SUCCESS=40 FAILED=0 (dry-run)`. Agent chạy `--dry-run` thấy exit code 0 tưởng ngon ăn, vội báo cáo hoàn tất cho user.
- **Thực tế lúc chạy thật văng lỗi ngay giây đầu tiên**:
  1. **Phase 1 (Exit Code 1)**: Script đồng bộ `sync-safe-workbook.py` quét fallback tự do ăn nhầm cột `PASS MAIL` (`Emma2004wOjd`) gán làm Serial máy vào `taikhoan_run_safe.xlsx`, gây lỗi `RuntimeError: Device map has conflicting valid serials for machine(s): 1..80` trên 70+ máy.
  2. **Phase 2 (Exit Code 2)**: Runner 2FA bị truyền sai cờ CLI (`--all-online --workers 10` thay vì `--live --max-workers 10`), Python `argparse` văng lỗi cú pháp.
  3. **Lỗi Working Directory (CWD Pollution)**: Tiến trình PowerShell/Python chạy từ `C:\Users\Kibe` nuốt nhầm file rác cũ `C:\Users\Kibe\gmail_reg_v10.py` thay vì repo `D:\Taadaa\register gmail`, ném `AttributeError`.

---

## 3 Nguyên Tắc Bắt Buộc Khi Setup Hoặc Sửa Bất Kỳ Cron Job Nào

### 1. CẤM Tuyệt Đối Dùng Mock / `--dry-run` Để Nghiệm Thu
- Lệnh mock / dry-run chỉ kiểm tra logic rẽ nhánh của Python, không hề chạm tới process runner thực tế, không test được import, không test được nạp thiết bị và cú pháp CLI.
- Tuyệt đối không bao giờ dùng kết quả `--dry-run` làm bằng chứng nghiệm thu để chốt phiên hoặc báo cáo cho user.

### 2. Định Nghĩa Chuẩn Của "Chạy Giả Lập Đến Giờ Cron": Là Chạy Thật Với Lệnh Thật
- Khi user yêu cầu "chạy giả lập đến giờ cron chạy xem còn lỗi không":
  - Đó là yêu cầu **chạy lệnh thật với cờ bypass điều kiện giờ (`--force`)**, thực thi process thật qua đúng CLI runner trên máy thật (1-2 máy rảnh hoặc target cụ thể).
  - Không được nhầm lẫn giữa "giả lập giờ cron kích hoạt" và "mock dry-run không chạy gì".

### 3. Quy Trình 4 Bước Nghiệm Thu Cron Mới/Được Sửa
1. **Kiểm tra cú pháp & CLI Argparse thật**: Gọi `--help` hoặc chạy thử process runner thật với cờ `--limit 1` hoặc 1 row cụ thể xem process có nạp mượt mà không (không văng argparse exit code 2).
2. **Cô lập Working Directory (`cwd`)**: Luôn truyền tường minh `cwd=str(REPO_DIR)` trong `subprocess.run/Popen` để tránh nuốt nhầm file script rác ở thư mục user (`C:\Users\Kibe`).
3. **Chạy Live Canary máy thật**: Chạy thật trên 1-2 máy đang rảnh (unlocked, hết cooldown) để verify toàn bộ chuỗi nạp thiết bị, kết nối ADB và ghi nhận kết quả.
4. **Bảo đảm tính toàn vẹn dữ liệu (Data Persistence Verification)**: Sau khi chạy test, kiểm tra trực tiếp file đích (ví dụ file Excel `taikhoan_dat_v2_updated .xlsx`, `taikhoan_run_safe.xlsx` hoặc database SQLite) xem dữ liệu sinh ra (2FA secret, Gmail pass, log) đã được ghi nhận đúng cột và đúng giá trị hay chưa.
