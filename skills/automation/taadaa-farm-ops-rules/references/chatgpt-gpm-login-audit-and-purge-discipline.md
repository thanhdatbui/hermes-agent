# Kỷ Luật Vận Hành Kiểm Tra & Dọn Dẹp Tài Khoản ChatGPT GPM (login_audit_and_purge_deactivated.py)

## 1. Công Cụ Canonical & Phạm Vi Hoạt Động
- **Script chuẩn:** `python D:/Taadaa/tools/login_audit_and_purge_deactivated.py`
- **Các chế độ chạy:**
  - `--limit N`: Chạy N tài khoản (giới hạn an toàn cron định kỳ: `--limit 5`).
  - `--canary`: Chạy nhanh 2 tài khoản canary.
  - `--email <email>`: Kiểm tra 1 tài khoản đích danh.
  - `--file <path>`: Đổi nguồn danh sách tài khoản (mặc định: `D:/Taadaa/Hotmail/latest_bought_70.txt`).

## 2. Invariant Chạy Nền Cho Batch Audit (Tránh Timeout 60s)
- **Đặc tính thời gian:** Mỗi tài khoản GPM mất trung bình 20 - 30 giây (start profile GPM, mở CDP, load ChatGPT, submit mail, fetch OTP qua Graph API/Webmail, trích xuất token hoặc kiểm tra status, đóng & kill Chrome).
- **Vấn đề Foreground Timeout:** Batch 5 tài khoản tốn khoảng 110 - 150 giây. Do môi trường áp trần timeout foreground (`GUARD_DEVICE_FOREGROUND_TIMEOUT` <= 60s), lệnh foreground sẽ luôn bị exit 124 timeout.
- **Quy tắc bắt buộc:**
  - Với `--limit` $\ge 3$, BẮT BUỘC khởi chạy qua terminal nền:
    `terminal(command="python D:/Taadaa/tools/login_audit_and_purge_deactivated.py --limit 5", background=True, notify_on_complete=True)`
  - Thu thập kết quả qua `process(action='wait', session_id=..., timeout=240)`.

## 3. Kỷ Luật An Toàn Purge (Anti-False-Purge & O(1) Fast Skip)
- **Tiêu chuẩn Purge:** CHỈ purge tài khoản khi xuất hiện đúng dấu hiệu vô hiệu hóa không thể đảo ngược (`account_deactivated`, "đã bị xóa hoặc vô hiệu hóa").
  - Chụp screenshot bằng chứng vào `D:/Taadaa/runtime/artifacts/deactivated_<safe_email>.png`.
  - Cập nhật lifecycle state sang `DEAD_DEACTIVATED`.
  - Ghi audit trail vào `D:/Taadaa/logs/chatgpt_audit_trail.jsonl`.
  - Gọi `purge_account` xóa khỏi OmniRoute/9Router và database SQLite.
- **Cấm Purge Ảo khi UNKNOWN:** Khi lỗi OTP (Graph API 400, mail chưa về) hoặc không match marker login/deactivated, script trả về `UNKNOWN`. TUYỆT ĐỐI KHÔNG đánh dấu DEAD và KHÔNG purge tài khoản.
- **O(1) Fast Skip:** Các tài khoản đã được đánh dấu `DEAD_DEACTIVATED` trong `D:/Taadaa/runtime/chatgpt_account_lifecycle.json` sẽ tự động được bỏ qua ngay lập tức (`SKIPPED_DEAD`) mà không cần mở profile GPM, tiết kiệm proxy và RAM.

## 4. Đồng Bộ Token & Đầu Ra Nghiệm Thu
- Khi tài khoản `LIVE`:
  - Trích xuất session token `__Secure-next-auth.session-token` qua CDP cookie context.
  - Tự động nạp / update token vào OmniRoute (`:20129`) và Router (`:20128`).
- Báo cáo kết quả:
  - Báo cáo JSON: `D:/Taadaa/reports/chatgpt_lifecycle_report.json` chứa tổng số, số live, dead, skipped, unknown và chi tiết từng tài khoản.
