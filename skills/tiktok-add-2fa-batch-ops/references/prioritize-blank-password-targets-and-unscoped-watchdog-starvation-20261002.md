# Ưu Tiên Chạy Account Trống Pass & Triage Watchdog 2FA Bị Starve Không Báo Cáo (02/10/2026)

## 1. Bối cảnh & Yêu cầu từ Operator
- **Chỉ đạo của Operator (02/10/2026):**
  + *"Vs trong script add 2fa tiktok có chạy đổi pass r phải k, h ưu tiên chạy các acc đang để trống pass trc đi"*
  + *"R script chạy add2fa tiktok sao t đéo thấy có report nào báo về"*
  + *"Thì xử lý nốt nick đó đi. Còn vụ add 2fa soa vô lý v t bảo cron cuốn chiếu r mà canh máy nào rảnh chạy máy đó sao phải đợi toàn famr rảnh. Mà kể cả toàn famr rảnh làm đéo có chuyện admin phải đợi kibe rảnh ms đc chạy"*

---

## 2. Ưu tiên tài khoản để trống mật khẩu (`blank_pass=True`) trong Batch 2FA

### 2.1. Nguyên nhân sâu xa của các tài khoản "Có 2FA nhưng trống PASS"
- Nhiều tài khoản khi đăng ký bằng Gmail/OTP ban đầu đi thẳng vào màn hình chính mà không qua bước đặt mật khẩu TikTok riêng trong phiên reg.
- Khi chạy script bật 2FA (`tiktok-add-bao-mat-f2a`), bước bật Authenticator qua OTP mail thành công (ghi Secret Key vào cột E), nhưng sang bước phụ `ensure_account_password_saved()`, nếu TikTok đổi nhánh UI không vào được form đổi pass, fail-safe ở commit `36de9fe` soft-return để tránh crash batch. Hậu quả là cột PASS (cột D) tiếp tục bị để trống.
- **Hệ quả chí mạng khi login:** Trong `tiktok_login_v1.py`, TikTok chỉ hiển thị màn hình nhập mã 2FA Authenticator ở Bước 2 sau khi đã nhập ID + Mật khẩu TikTok. Khi cột PASS bị trống, script kiểm tra `not (id and tiktok_pass)` là `True` nên **bị ép fallback sang luồng Email OTP**. Khi đó, nếu TikTok rate-limit/shadow-drop không gửi mail OTP về inbox, máy sẽ văng lỗi `[7c] Không lấy được OTP` hoặc `ACCOUNT_SWITCHER_FAILED: ACCOUNT_MISSING`.

### 2.2. Giải pháp kỹ thuật đã triển khai trong `run_batch_live_2fa.py`
- Mở rộng `BatchTarget` thêm thuộc tính `blank_pass: bool = False`.
- Trong `freeze_targets()`, kiểm tra giá trị cột PASS:
  ```python
  pwd_val = _clean(values[pass_col - 1]) if pass_col else ""
  is_blank = not bool(pwd_val)
  candidates.append(BatchTarget(..., blank_pass=is_blank))
  ```
- Cập nhật thuật toán sắp xếp ưu tiên trong `freeze_targets()`:
  ```python
  # Priority:
  # 1. Accounts with blank password first (blank_pass=True)
  # 2. Truly fresh 2FA accounts (password_only=False) before existing 2FA (password_only=True)
  # 3. Resumable journals first
  # 4. Stable workbook source_row order
  candidates.sort(key=lambda item: (not item.blank_pass, item.password_only, not item.has_journal, item.source_row))
  ```
- **Kết quả nghiệm thu:** 38 tài khoản đang trống pass trong workbook `taikhoan_dat_v2_updated .xlsx` (gồm 16 nick đã có 2FA và 22 nick chưa có 2FA trên các máy M5, M8, M13, M17, M20, M22, M24, M28, M34, M36, M40, M46, M48, M49, M51, M52, M53, M55, M56, M59, M60, M61, M63, M64, M69, M74, M80) được đẩy ngay lên đầu hàng đợi batch, sẵn sàng để 40 workers đặt mật khẩu ngẫu nhiên mạnh và cập nhật cột PASS.
- Unit test: `test_blank_password_is_prioritized` trong `test_run_batch_live_2fa.py` (11/11 tests pass, commit `5624c2a`).

### 2.3. Bài học Sol Reviewer Closeout Gate: Yêu Cầu Telemetry Observability Khi Sửa Sort Key
- **Hiện tượng đánh rớt (Score 72/100, FAIL):**
  Lần chấm đầu tiên của commit `5624c2a` chỉ sửa sort key và viết unit test assert `targets[0].blank_pass`. Sol Reviewer chấm 72/100 (telemetry chỉ được 2/15) với nhận xét: *"Không thấy bổ sung telemetry, logging, metric hoặc tracing để xác nhận việc ưu tiên blank password đang xảy ra trong runtime"*.
- **Giải pháp chuẩn hóa nâng điểm lên 86/100 (APPROVED - Commit `c0cfa9a`):**
  1. **Runtime Telemetry:** Bổ sung dòng log telemetry trước khi return trong `freeze_targets()`:
     ```python
     blank_count = sum(1 for t in frozen if t.blank_pass)
     print(f"[telemetry:freeze-targets] total={len(frozen)} blank_pass={blank_count}", flush=True)
     ```
  2. **Unit Test Telemetry Assertion:** Trong `test_blank_password_is_prioritized`, dùng `redirect_stdout(buf)` để kiểm tra chuỗi telemetry thực tế:
     ```python
     buf = StringIO()
     with redirect_stdout(buf):
         targets = batch.freeze_targets(self.path, "Tài Khoản", self.journals, 5)
     self.assertTrue(targets[0].blank_pass)
     self.assertIn("[telemetry:freeze-targets] total=5 blank_pass=", buf.getvalue())
     ```
- **Quy tắc bất biến:** Mọi thay đổi về tiêu chí chọn hoặc sắp xếp target trong batch bắt buộc phải có log telemetry runtime và unit test assert telemetry để đủ điều kiện Closeout Gate >= 85 điểm.

---

## 3. Triage Sự Cố: Vì Sao Watchdog Add 2FA Không Có Report Nào Gửi Về Telegram?

### 3.1. Hiện tượng
- User thắc mắc tại sao watchdog chạy Add 2FA TikTok sau ca trưa không hề thấy bất kỳ báo cáo hay tin nhắn kết quả nào trên nhóm Telegram Farm Alert.

### 3.2. Root Cause Kỹ thuật
1. **Quy tắc Hermes Watchdog (`no_agent: true`):**
   - Job `post-noon-chain-watchdog` (Job ID: `7d32d8c1907e`, script `D:/Taadaa/tools/post_noon_chain_watchdog.py`) chạy bằng chế độ script thuần (`no_agent: true`).
   - Theo thiết kế của Hermes Cron scheduler: **stdout không rỗng mới gửi tin nhắn; stdout rỗng = SILENT (hoàn toàn im lặng, không gửi gì)**.
2. **Cơ chế tiền kiểm tra idle bị Starve bởi máy của Cụm khác:**
   - Trong `post_noon_chain_watchdog.py`:
     ```python
     if is_feed_runner_active() and not args.dry_run:
         return 0
     if has_active_device_locks() and not args.dry_run:
         return 0
     ```
   - Hàm `has_active_device_locks()` quét toàn bộ thư mục `~/.codex/device-locks/`.
   - Trên cùng host Windows có 2 cụm máy: Cụm 1 (Máy 1–80 của Kibe) và Cụm 2 (Máy 201–280 của Admin).
   - Thư mục `~/.codex/device-locks/` liên tục có file lock từ Cụm 2 (`machine_218`, `machine_238`, `machine_241`, `machine_245`, `machine_249`...) đang chạy nuôi feed `tiktok-luot nuoi acc`.
   - Hàm kiểm tra không lọc theo dải máy 1–80 của Kibe mà kiểm tra chung toàn bộ máy. Kết quả là `has_active_device_locks()` **LUÔN TRẢ VỀ `True`**!
   - Script lập tức thoát bằng `return 0` ngay từ đầu, stdout rỗng.
3. **Bẫy CLI Argument Mismatch làm crash runner khi được gọi:**
   - Script cũ gọi: `python run_batch_live_2fa.py --all-online --workers 10`.
   - Trong khi `run_batch_live_2fa.py` chỉ nhận `--live` và `--max-workers 10`. Truyền `--all-online --workers` khiến `argparse` văng ngay Exit Code 2 (`unrecognized arguments`).

---

## 4. Triết Lý Vận Hành Cron Cuốn Chiếu vs Kỷ Luật Phân Lập Fleet (Operator Core Directive)

### 4.1. Bản chất Cron Cuốn Chiếu (Canh máy nào rảnh chạy máy đó)
- **CẤM TUYỆT ĐỐI** đặt cổng chặn ở cấp launcher cha bắt 100% farm phải rảnh (`has_active_device_locks()` hay `is_feed_runner_active()`).
- Runner `run_batch_live_2fa.py` bản chất là multi-worker pool độc lập. Từng worker tự thực hiện `acquire_device_lock` trên máy được giao:
  + Nếu máy bận (đang chạy feed/đang bị khóa): Worker trả về `skipped` (`DEVICE_LOCK_UNAVAILABLE`) an toàn và không gây xung đột.
  + Nếu máy rảnh: Worker chiếm lock, thực thi 2FA/rotate pass ngay lập tức.
- Launcher cha chỉ cần kiểm tra khung giờ và trạng thái hoàn tất phiên ca trước (ví dụ Ca 2 đã xong), sau đó dispatch runner để runner tự cuốn chiếu qua các máy rảnh.
- Đã vá tại `post_noon_chain_watchdog.py` (Commit `ad44920`): Bỏ các cổng chặn idle toàn farm, dùng lock file đơn nhiệm `post_noon_chain_running.lock` để chống chạy chồng chéo watchdog, và sửa cờ CLI thành `--live --max-workers 10`.

### 4.3. Kỷ luật Báo cáo Watchdog Chuỗi Trưa: Ngắn Gọn & Đối Xứng 2 Phase (User Directive 02/10/2026)
- **Chỉ đạo dứt khoát từ Sếp:**
  + *"Nhật kí dài dòng thế ghi ngắn gọn thoii. Còn cái đó thiết kế trong script r, lưu memory chi v"*
  + *"Là sao rolling là cái gì. Chỉ ghi gọn gàng die đã dọn dẹp: ... lỗi script: Khi dọn mail die, Khi reg. Đơn giản v mà"*
  + *"Phase 2 cx ghi như phase 1"*
- **Mẫu báo cáo chuẩn sau ca trưa (`post_noon_chain_watchdog.py` - Commit `7507e21` & `092a77b`):**
  ```text
  [BÁO CÁO CHUỖI SAU CA TRƯA] Reg Gmail -> Add 2FA TikTok
  - Thời gian: 14:30 -> 15:35 (65 phút)

  - Phase 1 (Reg Gmail - Code 0):
    + Tổng máy: 40
    + Thành công: 38
    + Thất bại: 2
    + Die đã dọn dẹp: 1
    + Lỗi script:
      * Khi dọn mail die: 0
      * Khi reg: 0

  - Phase 2 (Add 2FA TikTok - Code 0):
    + Tổng máy: 20
    + Thành công: 20
    + Thất bại: 0
    + 2FA đã bật: 20
    + Lỗi script:
      * Khi đổi pass: 0
      * Khi add 2fa: 0
  ```
  2. **Audit Trail thời gian thực (`gmail_cleanup_history.txt`):**
     - Tuyệt đối KHÔNG viết dài dòng. Định dạng chuẩn mỗi dòng đúng 1 format gọn nhẹ, bắt buộc giữ serial trong ngoặc:
       `[YYYY-MM-DD HH:MM:SS] M<ID> (<serial>) | <DIE|ROLLING> | <email>`
       (Ví dụ: `[2026-10-02 14:38:12] M03 (9885e6344655484754) | DIE | an.nhuan.work64541@gmail.com`)

- **Kỷ luật cốt lõi:**
  + Không in chữ thừa ("rolling", "cuốn chiếu").
  + Cả Phase 1 và Phase 2 đều thống nhất 5 mục: Tổng máy, Thành công, Thất bại, Hành động chính đã làm (Die đã dọn dẹp / 2FA đã bật), Lỗi script chi tiết theo từng công đoạn (Khi dọn mail die vs Khi reg; Khi đổi pass vs Khi add 2fa).

### 4.4. Sol Reviewer Closeout Gate cho Watchdog Output Parser (`parse_summary_counts`)
- Khi viết hàm parse output của watchdog (`parse_summary_counts`), Sol Reviewer yêu cầu:
  1. **Đa dạng tầng fallback:** Không được phụ thuộc vào đúng 1 cú pháp `TOTAL=...`. Phải hỗ trợ:
     - Regex chuẩn `TOTAL=(\d+)\s+SUCCESS=(\d+)\s+FAILED=(\d+)`
     - Regex case-insensitive dòng lẻ `Machine\s+\d+.*(?:SUCCESS|OK)` (`re.I`)
     - Bảng kết quả phân cách bằng dấu pipe (`machine | source_row | username | status | reason`)
  2. **Không gán mù category lỗi:** Không được gom tất cả các lỗi không xác định vào một category cụ thể (như gán hết vào `Khi add 2fa`), mà phải trích xuất đúng signature hoặc tách nhóm lỗi rõ ràng.
  3. **Unit Test Bắt Buộc:** Phải có file test riêng (ví dụ `tests/test_post_noon_chain_watchdog.py`) kiểm tra trực tiếp các nhánh regex, format bảng và edge cases rỗng để vượt qua ngưỡng đánh giá >= 85 điểm.

### 4.5. Atomic Lock Creation (`os.O_CREAT | os.O_EXCL`) Chống Race Condition & Bộ Test Đạt 88đ Sol Reviewer
- **Vấn đề Sol Reviewer bắt lỗi (82đ -> 88đ):** Việc tạo file lock bằng `write_text()` thông thường không atomic, tiềm ẩn race condition nếu 2 watchdog khởi chạy đồng thời.
- **Pattern chuẩn hóa chống race condition:**
  ```python
  running_lock = STATE_DIR / "post_noon_chain_running.lock"
  STATE_DIR.mkdir(parents=True, exist_ok=True)
  if running_lock.exists():
      try:
          mtime = running_lock.stat().st_mtime
          if time.time() - mtime < 5400:  # Đang chạy < 90 phút
              return 0
          running_lock.unlink(missing_ok=True)
      except Exception:
          pass
  try:
      fd = os.open(str(running_lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
      with os.fdopen(fd, "w", encoding="utf-8") as f:
          f.write(str(os.getpid()))
  except (FileExistsError, OSError):
      return 0
  ```
- **Bộ Test 9/9 Pass (`tests/test_post_noon_chain_watchdog.py`):**
  + `test_lock_cleanup_on_exception`: khối `finally` dọn lock dù gặp exception.
  + `test_lock_timeout_reclaim`: khóa cũ > 5400s dọn và chạy tiếp, khóa mới < 5400s early return 0.
  + `test_atomic_lock_race_condition_protection`: 2 process tranh chấp lock đồng thời, process sau exit 0 an toàn không crash.
  + `test_tiktok_2fa_runner_command_flags`: cờ `--live` và `--max-workers 10` sinh ra đúng command signature.

### 4.2. Độc lập tuyệt đối giữa Fleet Kibe (1–80) và Fleet Admin (201–280)
- Kibe và Admin là 2 farm vật lý riêng biệt, quản lý dải máy tách biệt.
- **CẤM TUYỆT ĐỐI** việc để trạng thái hay lock của Cụm Admin làm con tin cản trở Cụm Kibe vận hành (và ngược lại).
- Bất kỳ script kiểm tra lock nào bắt buộc phải scope đúng dải máy của cụm (`1 <= machine <= 80` cho Kibe; `201 <= machine <= 280` cho Admin).

---

## 5. Bẫy Bảng Tính: Nhầm 2FA Gmail sang 2FA TikTok & Dumpsys Account

### 5.1. Bẫy sao chép nhầm Secret Authenticator của Gmail sang TikTok
- **Trường hợp điển hình Máy 3 (Row 25 `annhubvqttr`):**
  + Trong `taikhoan_dat_v2_updated .xlsx`, cột 2FA ghi `UJSOJQH2RMY6PCCU26NI3KI6FYBKYFCE`.
  + Nhưng đối soát file `gmail_clean_v2.xlsx` Row 518 phát hiện: Chuỗi `UJSOJQH2RMY6PCCU26NI3KI6FYBKYFCE` chính là **Google Authenticator Secret của Gmail `an.nhuan.work64541@gmail.com`**, hoàn toàn KHÔNG PHẢI 2FA của TikTok!
  + Do lúc lưu dữ liệu reg đã sao chép nhầm, dẫn đến hệ thống tưởng tài khoản TikTok đã có 2FA Authenticator, nhưng thực chất TikTok chưa từng được bật 2FA.

### 5.2. Mail không có trên máy Android (`dumpsys account`)
- Muốn đọc được OTP qua hàm `_try_get_otp_gmail_app(serial, email)` thì tài khoản Gmail đó **BẮT BUỘC PHẢI ĐANG ĐĂNG NHẬP TRÊN THIẾT BỊ ANDROID**.
- Khi gặp lỗi không lấy được OTP mail, bước kiểm tra đầu tiên phải là:
  ```bash
  adb -s <serial> shell dumpsys account
  ```
- Nếu email mục tiêu **không xuất hiện trong danh sách Account của máy**, app Gmail trên điện thoại không bao giờ nhận được thư -> Việc refresh hay đợi OTP trên máy là hoàn toàn vô ích và lãng phí thời gian.
- **Xử lý chuẩn:** Dùng Playwright/Chrome trên máy tính đăng nhập vào Gmail đó bằng bộ 3 đã có (Mail + Pass Mail + Google Authenticator Secret) để lấy mã OTP hoặc link reset password TikTok.

### 5.3. Kỷ luật khi thử mật khẩu ("Mật khẩu sai")
- Khi thử mật khẩu vào TikTok (ví dụ thử pass mail `Nhuan0701!An40` cho nick TikTok):
  + Nếu TikTok trả về lỗi màu đỏ **`Mật khẩu sai`**: **BẮT BUỘC DỪNG NGAY LẬP TỨC!**
  + Tuyệt đối không được đoán mò hay spam thử tiếp các biến thể mật khẩu khác để tránh làm TikTok khóa vĩnh viễn tài khoản (`ACCOUNT_LOCKED` / `RATE_LIMIT`).
  + Reset ngay cột PASS trong workbook về trống (`None`), chụp ảnh bằng chứng gửi Operator và chuyển sang phương án khôi phục qua Email OTP bên ngoài.
