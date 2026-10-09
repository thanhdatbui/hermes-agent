# Watchdog DB Guard & Three-Way Sync Contract

## 1. Provider Guard Before Mutation (Chống ghi nhầm account / Cross-Provider Poisoning)
Khi watchdog tự động hồi sinh (revive) hoặc refresh credential (session token / cookie / oauth key):
- **Bắt buộc** query xác thực `provider` từ `provider_connections` trước khi thực hiện `UPDATE`:
  ```python
  cur.execute("SELECT provider, name FROM provider_connections WHERE id=?", (cid,))
  conn_row = cur.fetchone()
  if not conn_row or conn_row[0] != expected_provider:
      return False, f"Guard rejected: Connection {cid} does not belong to {expected_provider} provider"
  ```
- **Lý do**: Nếu connection ID bị lệch, tái sử dụng, hoặc gọi nhầm hàm giữa các pool (`chatgpt-web` vs `antigravity` vs `codex`), câu lệnh `UPDATE` sẽ ghi đè credential của provider khác, gây hư hỏng toàn bộ routing của provider đích.

## 2. Environment Override cho DB_PATH
- Tuyệt đối không hardcode cứng đường dẫn SQLite database nếu muốn script có thể test tự động.
- Pattern chuẩn:
  ```python
  DB_PATH = os.environ.get("OMNI_DB_PATH", os.path.expanduser(r"~/.omniroute/storage.sqlite"))
  ```
- Giúp các integration test tạo isolated SQLite DB tạm (`temp_integration.sqlite`), tạo schema giả lập đầy đủ `provider_connections` và `combos` để kiểm thử logic mutation và rollback mà không bao giờ động chạm vào DB production.

## 3. Quy Trình 3-Way Sync Cho Scripts Watchdog & Bẫy Drift Runtime
Khi cập nhật bất kỳ watchdog script nào trong Hermes/Omniroute (`cron_chatgpt_web_pool_watchdog.py`, `cron_omni_free_pool_updater.py`, `sync_gpm_lifecycle.py`, v.v.):
1. Source of truth (Repo): `D:\Taadaa\Hermes\deploy\hermes-home\scripts\<script_name>.py`
2. Local runtime: `C:\Users\Kibe\AppData\Local\hermes\scripts\<script_name>.py`
3. Shared cloud sync: `D:\OneDrive\Taadaa_Sync_Shared\hermes-cron\scripts\<script_name>.py`
4. Verification:
   - `python -m py_compile "D:\Taadaa\Hermes\deploy\hermes-home\scripts\<script_name>.py"`
   - `python -m pytest "D:\Taadaa\Hermes\tests\test_<script_name>.py" -v`

### Bẫy Đồng Bộ Một Chiều (One-Way Drift Trap) & Worker Out-of-Repo Sandbox
- **Nguyên nhân:** Worker subagent bị ràng buộc bởi `OUT OF REPO WHITELIST` (chỉ được cấp Scope Lock trong `D:\Taadaa`), không thể dùng `write_file` hay `patch` trực tiếp lên `C:\Users\Kibe\AppData\Local\hermes\scripts\`.
- **Rủi ro:** Nếu `cron_sync_watchdog.py` ở runtime Kibe chỉ so sánh `st_mtime` hoặc chỉ copy một chiều từ Kibe ra Deploy, bản vá của Worker trong repo `DEPLOY_SCRIPTS` sẽ **KHÔNG BAO GIỜ ĐƯỢC RUNTIME KÉO VỀ**, dẫn đến tình trạng code trong Git Deploy đã sửa đúng nhưng cronjob chạy ngầm vẫn thực thi code cũ.
- **Quy tắc bắt buộc trong `cron_sync_watchdog.py`:**
  - Vòng lặp đồng bộ bắt buộc duyệt `DEPLOY_SCRIPTS` và copy sang `KIBE_SCRIPTS` trước, kiểm tra: `if force or not dst_k.exists() or f.stat().st_mtime > dst_k.stat().st_mtime or f.stat().st_size != dst_k.stat().st_size:`.
- **Cơ chế Cầu Nối Cưỡng Chế (Forced Bridge via Wrapper):**
  - Khi script runtime bị kẹt phiên bản cũ chưa có logic kéo 2 chiều, sử dụng wrapper chạy PowerShell hợp lệ (ví dụ `sync-orchestration-skills.ps1` được gọi bởi cronjob `7e576815788f`) để thực thi `Copy-Item -Force` đè các file từ deploy sang runtime.

## 4. OpenPyXL Mock Caveat Trong Watchdog Tests
Khi mock workbook cho `load_accounts_credentials`:
- Script thường duyệt qua các sheet: `for sheetname in wb.sheetnames: ws = wb[sheetname]`
- Do đó mock object cần định nghĩa cả:
  - `mock_wb.sheetnames = ["Sheet1"]`
  - `mock_wb.__getitem__.return_value = mock_ws` (hoặc mock_ws gán tương ứng)
  - `mock_ws.iter_rows.return_value = ...`
- Nếu chỉ mock `mock_wb.active`, vòng lặp `wb.sheetnames` sẽ trả về rỗng hoặc lỗi và không nạp được credential nào.

## 5. Transient CDP Socket Bind Retry & Multi-Worker Concurrency Protection
- **Triệu chứng**: Khi morning watchdog mở đồng thời nhiều worker (`ThreadPoolExecutor(max_workers=5)`), GPM Local API trả về `remote_debugging_address` (ví dụ `127.0.0.1:53001`) ngay khi tạo tiến trình Chrome, nhưng Chromium 142 trên Windows có thể mất 1–3 giây để hoàn tất khởi động và bind socket lắng nghe CDP.
- **Hậu quả**: Gọi `connect_over_cdp` ngay lập tức sẽ ném ngoại lệ `BrowserType.connect_over_cdp: connect ECONNREFUSED` và làm watchdog kết luận sai rằng profile bị lỗi, trong khi tài khoản và profile hoàn toàn bình thường.
- **Pattern chuẩn hóa**: Bọc `connect_over_cdp` trong retry loop tối thiểu 3 lần với backoff 1.5s – 2s:
  ```python
  with sync_playwright() as p:
      browser = None
      for _ in range(3):
          try:
              browser = p.chromium.connect_over_cdp(f"http://{cdp_addr}")
              break
          except Exception:
              time.sleep(2)
      if not browser:
          return None
      context = browser.contexts[0]
  ```
- **Đồng bộ hóa**: Sau khi chỉnh sửa script tại `~\AppData\Local\hermes\scripts`, chạy `python ~/AppData/Local/hermes/scripts/cron_sync_watchdog.py` để tự động đồng bộ sang repo deploy (`D:\Taadaa\Hermes\deploy\hermes-home\scripts`) và OneDrive shared (`D:\OneDrive\Taadaa_Sync_Shared\hermes-cron\scripts`).

## 6. Pruning Deactivated Upstream Accounts & Dangling Combo Reference Prevention
- **Triệu chứng**: Upstream OpenAI chuyển hướng đăng nhập về `https://auth.openai.com/error?payload=<base64>`. Khi giải mã base64 chuỗi payload, dữ liệu JSON thể hiện rõ: `{"kind": "AccountDeactivated"}`.
- **Re-alert Loop Trap**: Nếu chỉ đặt `is_active = 0` hoặc `test_status = 'banned'` trong SQLite, watchdog tìm kiếm tài khoản inactive (`chatgpt_inactive = [c for c in conns if not (isActive and testStatus == 'active')]`) mỗi 05:00 sáng sẽ tiếp tục lặp lại việc bật GPM profile, thử đăng nhập, gặp lỗi timeout/payload, và spam bản tin cảnh báo rác.
- **Quy trình dọn dẹp dứt điểm**:
  1. *Lọc bỏ khỏi Combos trước*: Duyệt bảng `combos`, nếu connection nằm trong combo nào (ví dụ `gpt-web-luna`, `chatgpt-web-pool`), lọc bỏ `connectionId` khỏi mảng `models` và gọi `PUT /api/combos/{combo_id}` để lưu lại. Điều này ngăn chặn triệt để lỗi *dangling reference* khi router cố gắng gọi model trỏ vào connection không còn tồn tại.
  2. *Xóa Connection vĩnh viễn*: Gọi endpoint `DELETE /api/providers/{connection_id}` cho cả 2 connection liên quan của OpenAI (`chatgpt-web` và `codex`).
  3. *Bảo toàn Cross-Provider Isolation*: TUYỆT ĐỐI KHÔNG xóa hay vô hiệu hóa connection `antigravity` của cùng email đó, vì Antigravity sử dụng hạ tầng Google Cloud Code / Gemini OAuth độc lập hoàn toàn với chính sách vô hiệu hóa của OpenAI.

## 7. Phân Loại Chữ Ký Lỗi Watchdog & Tự Động Phục Hồi Dứt Điểm (Self-Healing Contracts)
- **Chữ ký lỗi phổ biến trong báo cáo Watchdog ("Cần chú ý")**:
  1. `Validate fail: HTTP Error 400: Bad Request`:
     * *Cơ chế*: Watchdog mở profile GPM, cookie trích xuất gửi sang `/api/providers/validate` bị OmniRoute trả về HTTP 400 do phiên `chatgpt.com` hết hạn.
     * *CẤM BÁO LỖI DỪNG SỚM*: Watchdog TUYỆT ĐỐI KHÔNG ĐƯỢC chỉ dừng lại ở bước validate cookie cũ rồi ném lỗi 400.
     * *Hành vi tự động hóa bắt buộc (Auto-Relogin Flow)*:
       1. Gọi `context.clear_cookies()` để dọn sạch rác phiên hỏng.
       2. Quét click nút `Log in / Đăng nhập` (`button[data-testid="login-button"]`, `button:has-text("Log in")`, `a:has-text("Log in")`).
       3. Tra cứu `PASS CHATGPT` tại Cột L workbook `taikhoan_dat_v2_updated .xlsx` qua hàm `get_chatgpt_password_from_workbook`.
       4. Điền email + mật khẩu chính chủ vào form OpenAI, xử lý Google SSO / Onboarding (tuổi).
       5. Trích xuất session cookie mới (`__Secure-next-auth.session-token`), validate và cập nhật `is_active = 1` trên OmniRoute.
  2. `Timeout bắt OAuth code` (Antigravity Google OAuth Challenge):
     * *Cơ chế*: Xảy ra khi connection `antigravity` bị upstream 401, re-auth gặp màn hình xác minh của Google.
     * *CẤM CHỜ TIMEOUT MÙ 90S*: Hệ thống đã có sẵn cơ chế phối hợp với Samsung Galaxy S7 (`run_oauth_s7_pipeline.py`). Watchdog bắt buộc phải liên thông gọi sang pipeline S7:
       1. Nếu gặp `challenge/selection`: Tự động click option 8 *"Mã bảo mật trên điện thoại"*.
       2. Nếu gặp `challenge/ootp` hoặc header Galaxy S7: Gọi `get_s7_security_code(machine_id, serial, email)` qua ATX-Agent port 7912 bốc mã 10 số offline điền vào PC.
       3. Nếu gặp `challenge/dp`: Gọi `approve_s7_google_prompt(machine_id, serial, target_pin, target_email)` để bấm duyệt "Có" / chọn số PIN trên màn hình S7.
- **Tính độc lập trạng thái đa Provider (Cross-Provider Status Independence)**:
  * Một email sở hữu tối đa 3 connection độc lập trong `provider_connections` (`chatgpt-web`, `codex`, `antigravity`).
  * *Hiện tượng thực tế*: Một tài khoản (ví dụ `luunhu290719@gmail.com`) có thể xuất hiện đồng thời ở mục "Đã hồi sinh ChatGPT" (nhánh Web & Codex sống 100%) và mục "Cần chú ý" (nhánh Antigravity bị timeout bắt OAuth code).
  * *Kỷ luật bất biến*: CẤM ngộ nhận một tài khoản bị lỗi ở 1 provider là hỏng toàn bộ. Không bao giờ tắt chùm hoặc xóa connection khi chưa đối soát chính xác `provider` cụ thể bị lỗi.
