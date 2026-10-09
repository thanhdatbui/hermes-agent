# Parallel Reg Workbook Merge, Writer Identity Guard & Password Gap Prevention

## 1. Bản chất kiến trúc lưu kết quả Reg Gmail song song
- Nhằm tránh xung đột file lock (`PermissionError: [Errno 13]`) khi 15–40 máy S7 cùng ghi đè vào `gmail_clean_v2.xlsx` / `master_gmail_manager.xlsx`, cờ trực tiếp `--write-workbook-success` bị deprecated.
- Từng tiến trình worker reg trên thiết bị ghi file JSON riêng lẻ vào `--result-dir` (ví dụ: `machine_04.success.json`).
- Sau khi toàn bộ batch máy kết thúc, `run_parallel.ps1` gọi đúng 1 lần:
  `python scripts/merge_success_results.py --result-dir ... --workbook ...`

---

## 2. Các điểm nghẽn & bẫy lỗi (Pitfalls)

### Bẫy 1: Thiếu biến môi trường Writer ID (`BLOCKED_EXPECTED_WRITER_ID_MISSING`)
- **Triệu chứng**: Bước merge văng lỗi `WorkbookError("BLOCKED_EXPECTED_WRITER_ID_MISSING:gmail_clean_v2")` với exit code 2. Kết quả reg trên S7 thành công nhưng Excel hoàn toàn không được ghi.
- **Nguyên nhân**: `single_writer_workbook_update` của `automation_core.workbook` bắt buộc phải có `expected_writer_id` và `declared_writer_id`. Khi chạy qua launcher/cron mà không export sẵn `GMAIL_WRITER_ID`, `os.environ.get("GMAIL_EXPECTED_WRITER_ID", "")` bị rỗng.
- **Giải pháp chuẩn hóa**: Bắt buộc có fallback mặc định giống `gmail_reg_v10.py`:
  ```python
  writer_id = os.environ.get("GMAIL_WRITER_ID") or "taadaa-writer-3c47f89f35e44795a79267e09fbcc72d"
  expected_writer_id = os.environ.get("GMAIL_EXPECTED_WRITER_ID") or writer_id
  ```

### Bẫy 2: Bỏ qua cập nhật mật khẩu khi Email đã có sẵn (`existing_email` skip trap)
- **Triệu chứng**: Một số tài khoản đã có email trong sheet nhưng cột mật khẩu bị `None` hoặc trống. Khi chạy merge bù, script vẫn báo `SKIPPED machine X: email reason=existing_email`.
- **Nguyên nhân**: Logic kiểm tra trùng lặp thô sơ:
  `if email in workbook_emails: skip_reason = "existing_email"`
  bỏ qua toàn bộ dòng đã tồn tại, kể cả khi ô password chưa có dữ liệu.
- **Giải pháp**: Nếu email đã tồn tại nhưng ô password trong workbook rỗng, script bắt buộc phải cập nhật password cho dòng đó thay vì skip.

### Bẫy 3: Đứt gãy dây chuyền sang GPM OAuth & Antigravity Pool
- **Triệu chứng**: GPM watchdog báo có nhiều profile sẵn Google Session nhưng Pool Antigravity (`:20129`) đứng im không tăng số lượng acc LIVE.
- **Nguyên nhân gốc rễ**: `cron_gpm_oauth_full_pool.py` dùng `CredentialLookup` đọc password từ `master_gmail_manager.xlsx` và `gmail_clean_v2.xlsx`. Khi tài khoản thiếu pass trong Excel:
  `if not creds.get("password"): continue`
  Script âm thầm bỏ qua tài khoản đó, không nạp được OAuth vào OmniRoute.

---

## 3. Quy trình khắc phục & Đối soát khẩn cấp
1. **Tìm mật khẩu gốc**:
   - Tra cứu trong cấu hình batch (`run_batch_turn2_gmails.py`, `select_turn2_candidates.py`).
   - Tra cứu trong file log tổng `C:\Users\Kibe\AppData\Local\register-gmail\reg_log.txt` tại marker `[ACCOUNT_GEN]` hoặc step `[10] Password`.
   - Tra cứu lịch sử session Hermes SQLite qua `session_search`.
2. **Điền bù dữ liệu 2 chiều**:
   - Ghi đồng thời vào `master_gmail_manager.xlsx` (Sheet `Kibe_Farm_S7`, `Master_All`) và `gmail_clean_v2.xlsx` (Sheet `Gmail Accounts`).
   - Luôn chạy readback assert sau khi save workbook để đảm bảo dữ liệu đã xuống đĩa an toàn.
3. **Kích hoạt Feeder**:
   - Chạy thủ công hoặc trigger cronjob `gpm-oauth-full-pool-feeder` (job_id: `8ce4b722772f`) để giải phóng hàng đợi OAuth ngay sau khi nạp bù pass.
