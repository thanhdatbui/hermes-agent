# Case Study: Cron Setup & Live Simulation Verification Rules (13/09/2026)

## 1. Bối cảnh sự cố
- Watchdog chuỗi sau ca trưa (`post_noon_chain_watchdog.py`) chạy lúc 16:00 bị văng ngay trong vòng 1 phút, trả về 0 máy cho cả 2 phase (Reg Gmail Code 1, TikTok 2FA Code 2).
- Nguyên nhân gốc rễ:
  1. `sync-safe-workbook.py` (commit lúc 11:28) quét fallback serial không giới hạn cột, bốc nhầm `PASS MAIL` vào cột device serial, gây xung đột serial trên 70+ máy.
  2. `post_noon_chain_watchdog.py` gọi sai cờ CLI của runner 2FA (`--all-online --workers 10` thay vì `--live --max-workers 10`).
  3. Khi Coordinator test kiểm chứng, Coordinator chạy `--dry-run` (vốn chỉ là mock chuỗi text hardcode) và kết luận đã hết lỗi. Người dùng bức xúc vì mock không bảo đảm được khi tới giờ cron chạy thật sẽ không văng lỗi.
  4. Tiếp tục điều tra sâu khi chạy runner thật, phát hiện lỗi thiếu `cwd=str(GMAIL_REPO_DIR)`, khiến Python nạp nhầm file rác `gmail_reg_v10.py` ở thư mục user (`C:\Users\Kibe`), ném `AttributeError`.

## 2. Bài học & Quy tắc bắt buộc (Hard Invariants)

### Rule 1: CẤM DÙNG MOCK / DRY-RUN ĐỂ KẾT LUẬN VÀ CHỐT PHIÊN KHI SETUP/SỬA CRON
- Cờ `--dry-run` hoặc các hàm trả về mock string chỉ dùng để kiểm tra logic rẽ nhánh sơ bộ.
- TUYỆT ĐỐI CẤM dùng kết quả dry-run / mock làm bằng chứng nghiệm thu để báo cáo "đã hết lỗi" hoặc chốt phiên.
- **Bắt buộc:** Phải chạy giả lập thật (live simulation) bằng chính lệnh/entrypoint thực tế mà scheduler sẽ gọi (`--force` hoặc gọi runner với scope 1-2 máy rảnh) để kiểm chứng import, working directory, argument parsing và lock resolution.

### Rule 2: CÔ LẬP WORKING DIRECTORY (`cwd`) KHI SUBPROCESS GỌI SCRIPT
- Khi viết script wrapper / watchdog gọi script con ở các repo khác (như `register gmail`, `tiktok-add-bao-mat-f2a`), BẮT BUỘC truyền tham số `cwd=str(REPO_DIR)` trong `subprocess.run` / `Popen`.
- Nếu không set `cwd`, tiến trình con sẽ chạy với thư mục làm việc của tiến trình cha (thường là `C:\Users\Kibe`), dẫn đến:
  - Nạp nhầm file script trùng tên bản cũ ở thư mục user thay vì file mới trong repo.
  - Lỗi relative path tới file config, logs, dữ liệu.

### Rule 3: ĐẢM BẢO TÍNH TOÀN VẸN CỦA DỮ LIỆU ĐÍCH (2FA & GMAIL)
- Mọi script tự động hóa nhạy cảm (như Add 2FA TikTok):
  - Bắt buộc kiểm tra việc ghi dữ liệu trực tiếp vào Excel nguồn (`write_2fa` vào đúng cột `2FA`).
  - Phải có cơ chế tự động backup trước khi ghi và đối soát verification (`WORKBOOK_REOPEN_VERIFY_FAILED`).
  - Ghi nhật ký audit `[ACCOUNT_RECORD]` ra file log local để có bằng chứng đối soát khi có tranh chấp dữ liệu.
