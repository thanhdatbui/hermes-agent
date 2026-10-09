# Watchdog Đăng Nhập GPM Tối (Post-Evening GPM Login Watchdog) & Lọc Candidates

Tài liệu quy chuẩn cho watchdog tự động đăng nhập Gmail lên GPMLogin sau ca tối (`post_evening_gpm_login_watchdog.py`), kỹ thuật bắt kết quả subprocess chính xác, và thuật toán tuyển chọn candidates an toàn cho Farm.

---

## 1. Concurrency & Farm Safety Limits
- **MAX_WORKERS = 2** (tối đa 2 worker song song). Tuyệt đối không chạy 5-10 workers vì GPMLogin + Chromium CDP ngốn nhiều RAM, dễ gây tranh chấp taskbar, đụng độ tiến trình Chromium và làm crash máy host.
- **Stagger sleep = 5s** giữa các lần khởi chạy worker.
- **Proxy Constraint**: Mỗi proxy port tối đa 2 tài khoản / ngày (`MAX_LOGINS_PER_PROXY = 2`).
- **Machine Constraint**: Mỗi máy S7 (`mid`) chỉ chạy đúng 1 lần / ngày.
- **Idle Buffer**: Chỉ chạy khi máy rảnh và cách ca farm tiếp theo ít nhất 45 phút.

---

## 2. Quy trình Lọc Candidates Chuẩn Xác (Candidate Selection Filter)

Khi chọn danh sách Gmail để đăng nhập (`get_candidates`):

### A. Kiểm tra Profile GPM DB Toàn Cục (`get_all_gpm_emails()`)
- Không chỉ lọc theo `GroupId == 10` (nhóm Google_Live_Ready), vì hầu hết profile GPM nằm ở GroupId 0 hoặc 1.
- Quét toàn bộ DB SQLite GPM (`profile_data.db`):
  ```python
  def get_all_gpm_emails() -> set[str]:
      emails = set()
      try:
          conn = sqlite3.connect(GPM_DB)
          cur = conn.cursor()
          cur.execute("SELECT Name FROM profiles")
          for (name,) in cur.fetchall():
              m = re.search(r"([a-z0-9._%+\-]+@gmail\.com)", (name or "").lower())
              if m:
                  emails.add(m.group(1))
          conn.close()
      except Exception as e:
          log(f"Lỗi đọc GPM DB: {e}")
      return emails
  ```
- **BẮT BUỘC**: Nếu tài khoản trong danh sách chưa có profile trong GPM DB, BẮT BUỘC bỏ qua vì `run_oauth_s7_pipeline.py` sẽ văng lỗi `PROFILE_NOT_FOUND`.

### B. Đối soát `STATUS_JSON` (`oauth_pipeline_status.json`)
1. **`omniroute_success`**: Loại bỏ ngay các email đã có trong `omniroute_success` (tránh chạy lại các tài khoản đã đăng nhập và nạp token OmniRoute thành công).
2. **`cooldown_7days`**: Chỉ nhận tài khoản khi:
   - `retry_after <= today_str`
   - Chưa nằm trong `omniroute_success`
   - Không dính `excluded_khoalee` / `khoale`
   - Không dính `wrong_password_or_checkpoint`
   - Không nằm trong `ip_cooling_recaptcha` (hoặc đã hết hạn)
   - ĐÃ CÓ profile trong GPM DB.
3. **`excluded_khoalee` & Recovery Email KhoaLee**:
   - Loại trừ 100% email thuộc `excluded_khoalee` hoặc có chuỗi `khoale` trong email.
   - Loại trừ 100% tài khoản có `Recovery_Email` chứa `khoale` (ví dụ: `khoalemagic@gmail.com`, `khoaleemagic@gmail.com`) khi tra từ file Excel `master_gmail_manager.xlsx`.
4. **`wrong_password_or_checkpoint`**: Loại bỏ các email bị sai mật khẩu hoặc checkpoint chưa gỡ.
5. **`ip_cooling_recaptcha`**: Kiểm tra `retry_after`. Nếu `retry_after > today_str` (hoặc không có ngày hết hạn rõ ràng) thì phải loại bỏ để IP hạ nhiệt.

### C. 2FA Decoupling & CHATGPT_READY Priority Boost (Nhóm 2: Excel Candidates)
Khi đọc từ `master_gmail_manager.xlsx` (sheet `Kibe_Farm_S7`):
1. **Gỡ Bỏ Ràng Buộc Bắt Buộc 2FA (Decoupled 2FA Filter)**:
   - Trước đây script yêu cầu `two_fa` khác rỗng/NONE. Hiện tại đã **gỡ bỏ điều kiện lọc bắt buộc 2FA** khỏi watchdog (`post_evening_gpm_login_watchdog.py`) để cho phép các tài khoản chưa bật 2FA vẫn được tự động xử lý đăng nhập GPM bình thường.
   - Các tài khoản chỉ cần thỏa mãn: email hợp lệ, state không phải `DIE/BAN/SUSPENDED`, đã có profile trong GPM DB, không dính `omniroute_success`, `excluded_emails`, hay chuỗi `khoale`.
2. **Cơ Chế Priority Boost cho `CHATGPT_READY`**:
   - Đọc danh sách `completed_chatgpt` từ backlog state: `D:/Taadaa/runtime/kibe/cron-state/chatgpt_link_backlog_state.json`.
   - Kiểm tra cột Ghi Chú (cột 14 / index 13): nếu chứa chuỗi `chatgpt_ready` / `chatgpt` hoặc email đã có trong `completed_chatgpt` $\rightarrow$ gán `priority = 1` (`reason: "chatgpt_ready_priority"`).
   - Các email hợp lệ khác mang `priority = 2` (`reason: "ready_gpm_oauth"`).
   - **Thứ tự xử lý**: Thực hiện `candidates.sort(key=lambda x: x.get("priority", 2))` **trước khi** chạy qua bộ lọc giới hạn constraint proxy (`MAX_LOGINS_PER_PROXY`) và thiết bị (`seen_mids`). Điều này bảo đảm tài khoản đã sẵn sàng ChatGPT luôn được ưu tiên chiếm slot login trước.
3. **Đồng Bộ Mã Nguồn Kép (Dual Path Deployment)**:
   - File script watchdog tồn tại song song tại 2 vị trí:
     + `C:/Users/Kibe/AppData/Local/hermes/scripts/post_evening_gpm_login_watchdog.py`
     + `D:/OneDrive/Taadaa_Sync_Shared/hermes-cron/scripts/post_evening_gpm_login_watchdog.py`
   - Bắt buộc patch đồng thời cả 2 file và biên dịch `python -m py_compile` để đảm bảo Hermes cron local và farm sync OneDrive luôn đồng nhất 100%.

---

## 3. Pitfall: Bắt Kết Quả Subprocess (stdout vs stderr)

### Vấn đề:
Các runner Python như `run_oauth_s7_pipeline.py` sử dụng thư viện chuẩn `logging` (`logger = logging.getLogger(...)`). Mặc định Python logging xuất ra `sys.stderr`, khiến `proc.stdout` khi chạy qua `subprocess.run(..., capture_output=True)` hoàn toàn rỗng (`""`).
Nếu kiểm tra `success = "SUCCESS" in proc.stdout`, watchdog sẽ luôn đánh giá là thất bại (`✓ 0 | ✗ 10`).

### Giải pháp chuẩn:
Gộp cả stdout và stderr trước khi kiểm tra trạng thái, đồng thời xử lý cả trường hợp `ALREADY_SUCCESS`:
```python
proc = subprocess.run(
    [PYTHON_EXE, str(GPM_SCRIPT), email],
    capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600,
)
combined = (proc.stdout or "") + "\n" + (proc.stderr or "")
success = (
    (("SUCCESS" in combined and "LAUNCH_FAILED" not in combined and "EXCHANGE_FAILED" not in combined)
     or "ALREADY_SUCCESS" in combined)
)
```
Sau khi thành công, cập nhật `GroupId = 10` vào GPM DB và có thể trigger tiếp `batch_dual_oauth_5workers.py` cho ChatGPT-Web & Codex.
