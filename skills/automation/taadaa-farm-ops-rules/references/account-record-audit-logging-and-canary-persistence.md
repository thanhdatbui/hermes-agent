# Account Record Audit Logging & Canary Persistence Protocol

## 1. Context & Root Cause
Trong các tác vụ reg tài khoản (Gmail, TikTok) hoặc bảo mật (Add 2FA, Add Mail Khôi phục), xảy ra các sự cố nghiêm trọng:
1. **Mất mật khẩu khi chạy đơn lẻ (Canary/Test)**:
   - Code cũ thiết kế `persist_success_result` chỉ lưu khi có cờ batch `--result-dir`. Khi chạy canary (`python gmail_reg.py <stt> --ss`), script bỏ qua persistence (`[WORKBOOK_GUARD]`), vứt bỏ credentials chỉ lưu trong RAM.
   - Script không in mật khẩu ra log file để tránh lộ pass, dẫn đến khi tiến trình kết thúc thì mất vĩnh viễn không khôi phục được.
2. **Không thể truy vấn đối soát dữ liệu sau này**:
   - Khi cần tìm lại thông tin tài khoản vừa reg / add 2FA trên máy cụ thể, không có log file nào lưu vết tập trung.

## 2. Quy Tắc Bắt Buộc Đối Với Mọi Pipeline Reg / Add
Tất cả các script reg hoặc cập nhật bảo mật tài khoản BẮT BUỘC tuân thủ:

### Quy tắc 1: Log cấu trúc `[ACCOUNT_RECORD]` ngay trước khi persist
Trước bất kỳ lệnh ghi workbook hoặc ghi deferred JSON nào, BẮT BUỘC ghi 1 dòng log có format chuẩn:
- **Gmail Reg**:
  ```text
  [ACCOUNT_GEN] Generated {email} | pass: {acc['pass']}
  ```
- **TikTok Reg**:
  ```text
  [ACCOUNT_RECORD] STT: {stt} | Serial: {device_id} | Email: {email} | TikTok: @{handle} | TT_Pass: {tiktok_pw} | Mail_Pass: {mail_pw} | DOB: {dob} | Created: {created}
  ```
- **Gmail Add Recovery / Password**:
  ```text
  [ACCOUNT_RECORD] May {so_may} | Row {row_idx} | Gmail: {gmail} | Mail_KP: {value}
  [ACCOUNT_RECORD] May {so_may} | Row {row_idx} | Gmail: {gmail} | Password: {value}
  ```
- **TikTok Add 2FA**:
  ```text
  [ACCOUNT_RECORD] May: {target.machine} | Sheet: {target.source_sheet} | Row: {target.source_row} | Username: {target.username} | 2FA_Secret: {secret.strip()}
  ```

### Quy tắc 2: Fallback ghi trực tiếp vào Workbook khi chạy đơn lẻ
Nếu script phát hiện không có cờ `--result-dir` (chạy lẻ, canary watchdog, debug tay):
- CẤM bỏ qua persistence (`[WORKBOOK_GUARD]` silent skip).
- BẮT BUỘC dùng fallback atomic update (`single_writer_workbook_update` kết hợp hàm ghi hàng chuyên biệt) để ghi thẳng vào Excel nguồn, có backup tự động trước khi ghi.

### Quy tắc 3: Chống Zombie Summary Fallback
Trong các orchestrator pipeline chuỗi đêm (như `run_night_chain_pipeline.py`), khi tìm file kết quả/summary mới nhất:
- BẮT BUỘC kiểm tra `time.time() - summary_path.stat().st_mtime <= 10800` (ngưỡng tối đa 3 giờ).
- CẤM TUYỆT ĐỐI fallback nhặt summary file của ngày hôm trước khi batch hiện tại bị crash hoặc không sinh output mới.
