# Missing Account on Multi-Account Switcher: Triage & Auto-Login Recovery Flow

## 1. Hiện Tượng & Nguyên Tắc Vận Hành Cốt Lõi
Khi chạy batch Feed / Upload Hook, hệ thống phát cảnh báo:
```text
UploadHook: [ERROR] scripts.tiktok_workflow.state_machine: [ACCOUNT_SWITCHER_FAILED] select account failed: ACCOUNT_MISSING: expected account was not found.
FeedRunner: [FAIL] Lệch Profile/Nick TikTok (profile account mismatch / navigation target profile not found)
```
- **Quy tắc bất biến của User:** Cứ thiếu acc hoặc lệch profile (`ACCOUNT_MISSING`, `profile account mismatch`), BẮT BUỘC hệ thống phải tự động auto-switch sang nick đúng nếu đã có trong Switcher, hoặc kích hoạt flow `Thêm tài khoản` / reconcile nạp bù vào slot còn thiếu (`recovery_handler = "tiktok_login"` / `reconcile_tiktok_accounts.py`).
- **CẤM TUYỆT ĐỐI:** Cấm viện cớ an toàn, cấm viện cớ "sợ lệch nhịp batch" hay "sợ văng phiên liên đới" để fail-closed dừng máy bắt người vận hành thao tác thủ công. Cả ca Đăng video lẫn ca Nuôi feed đều phải tự động recovery nick. Script login đã được thiết kế sẵn nhánh mở Switcher và tap `Thêm tài khoản`.

## 2. Kiến Trúc Kích Hoạt Tự Động (Đã Fix & Chuẩn Hóa)

### A. State Machine nhận diện thiếu acc (`scripts.tiktok_workflow.state_machine.py:5575`)
- Khi Switcher không tìm thấy target account (`err_msg` chứa `account_missing` hoặc `expected account was not found`):
  Hệ thống lập tức kích hoạt:
  ```python
  self.context.is_login_required = True
  self.context.is_no_account_login_required = True
  self.context.error = f"[LOGIN_RECOVERY_REQUIRED] {err_msg}."
  self.context.checkpoint["recovery_handler"] = "tiktok_login"
  ```
  -> `run_post.py` trả về exit code 4 với trạng thái `LOGIN_RECOVERY_REQUIRED`.

### B. Auto Login Handler qua Batch Runner (`run_tiktok_upload_batch.ps1`)
- Khi nhận `LOGIN_RECOVERY_REQUIRED`, batch runner khởi chạy `Start-LoginRecoveryRunner` để tự động chạy script login:
  ```powershell
  if (-not $ProfileSmoke -and $report -and $report.status -eq 'LOGIN_RECOVERY_REQUIRED' -and $runner.LoginRecoveryAttempt -eq 0) {
      $active[$key] = Start-LoginRecoveryRunner -Machine $runner.Machine
      continue
  }
  ```
- Khi login recovery exit code 0, runner đưa máy trở lại hàng đợi `$pending` để retry ca đăng video tự động một lần.

### C. Cấu hình lệnh Login Handler (`config-admin.yaml` & `config.example.yaml`)
- `login_recovery_command` được cấu hình để gọi trực tiếp script login tự động:
  ```yaml
  login_recovery_command:
    - "D:\\Taadaa\\python-envs\\automation\\Scripts\\python.exe"
    - "-X"
    - "utf8"
    - "D:\\Taadaa\\Tiktok_Reg\\tiktok_login_v1.py"
    - "{machine}"
    - "--all"
    - "--allow-parent-lock"
  ```
  **Lưu ý bắt buộc:**
  1. **Cờ `--all`:** BẮT BUỘC phải có `--all`. Nếu không có `--email` hay `--all`, `tiktok_login_v1.py` sẽ abort với lỗi: `STOPPED: Co nhieu account du info. Dung --email <mail|id> de chi ro account can login, hoac --all de chay tat ca account usable.` Với `--all`, script sẽ quét toàn bộ danh sách usable: nick nào đã có trong Switcher sẽ nhận diện `already_logged_in` và bỏ qua; chỉ nick thiếu mới bị đưa vào flow `tap_add_account` để login.
  2. **Python environment:** Trỏ đúng python của venv automation (`D:\Taadaa\python-envs\automation\Scripts\python.exe`) và cờ `-X utf8` để tránh lỗi encoding `cp1252` trên console Windows.
  3. **Host config (`taadaa_host.py`):** Trên cụm Admin (máy 201+), biến môi trường `TAADAA_HOST_CONFIG` phải là `D:/Taadaa/machine-config/admin.yaml` để script nạp đúng tracking workbook của Admin (`taikhoan_dat_v2_updated .xlsx`), không bị rơi về path của Kibe khiến 0 accounts được load.
  4. **Pitfall OneDrive dehydrated file (`RecallOnDataAccess` / `0x400000`):** Nếu `openpyxl` báo `TARGET_INVENTORY_READ_FAILED: OSError` (`[Errno 22] Invalid argument`), kiểm tra thuộc tính file workbook `taikhoan_run_safe.xlsx`. Nếu dính cờ `4199968` (RecallOnDataAccess/Offline), cần re-hydrate file bằng cách đọc stream byte và ghi đè lại nội bộ để file nằm thật sự trên ổ cứng.

### D. Auto Login Recovery trong Feed Runner (`tiktok-luot nuoi acc`)
- Khi Feed Runner kiểm tra Profile và gặp `profile account mismatch` hoặc target username không có trong Switcher:
  1. Thử mở Account Switcher để auto-switch nếu nick mục tiêu đã đăng nhập ở slot khác.
  2. Nếu Switcher hoàn toàn thiếu nick: CẤM fail-closed nhả máy; kích hoạt handler gọi `_run_fast_targeted_login()` (`tiktok_login_v1.py <machine> --email <nick> --ss --allow-parent-lock`) hoặc fallback Reconcile (`reconcile_tiktok_accounts.py`).
  3. **Pitfall biến môi trường & Workbook cụm kép (Dual-Cluster Trap):**
     - Trong `flows/feed_swipe_smoke.py`, các hằng số mặc định `DEFAULT_RECONCILE_WORKBOOK`, `DEFAULT_RECONCILE_LOGIN_WORKBOOK`, `DEFAULT_RECONCILE_PROXY_MAPPING` trỏ về cụm Kibe.
     - Khi `int(machine_id) >= 200`: BẮT BUỘC logic khởi tạo `workbook`, `login_workbook`, `proxy_mapping` phải trỏ về thư mục Admin (`D:\OneDrive\TaadaaData\admin\...`), đồng thời nạp `clean_env["TAADAA_HOST_CONFIG"] = r"D:\Taadaa\machine-config\admin.yaml"`. Nếu thiếu bước này, script gọi Reconcile với file Kibe sẽ văng lỗi: `CONFIG_ERROR: machine <N> has no serial in workbook` và fail-closed ngay lập tức!
  4. **Pitfall False-Positive `verified = True` sau khi tap Switcher:**
     - Trong `profile_preflight`, nếu UI chưa render kịp `@handle` khiến `not recaptured_username = True`, không được mặc định cho qua (`verified = True`) vì máy sẽ lướt feed nhầm trên nick cũ và bị phát hiện ở `_verify_profile_after_session` cuối ca gây lãng phí tài nguyên và lệch nhịp.

### E. Gate 2 Monolith Patch Anchor Pitfall
- Khi chuẩn bị Patch Contract O(1) cho monolith lớn (`feed_swipe_smoke.py` > 20.000 dòng):
  - Tuyệt đối tránh các anchor generic ngắn như `workbook = Path(` vì nó khớp cả dòng `login_workbook = Path(`, gây vi phạm Gate 2 `ANCHOR_NOT_UNIQUE (c == 2)`.
  - Luôn mở rộng anchor với token duy nhất tuyệt đối (như `reconcile_script = Path(`) để đảm bảo `c == 1` trước khi dispatch Worker.

### F. Pitfall Môi Trường Canary Runner Khi Nghiệm Thu Máy Admin (`canary_runner.py`)
- **Hiện tượng:** Khi chạy `python D:/Taadaa/tools/canary_runner.py --repo "tiktok-luot nuoi acc" --machine 261 --row 1`, canary runner fail ngay lập tức ở giây đầu tiên:
  ```text
  Host guard error: MACHINE_OUT_OF_RANGE: machine=261 không thuộc host kibe (range 1-80). Dừng fail-closed.
  ```
- **Nguyên nhân:** Dù tool đã truyền `--account-workbook` trỏ về Admin, nhưng child `env` khi gọi runner subprocess lại kế thừa môi trường mặc định của Kibe (`TAADAA_HOST_CONFIG = kibe.yaml`), khiến `taadaa_host.py` kích hoạt chốt an toàn chặn máy ngoài range [1, 80].
- **Quy chuẩn sửa đổi:** Trong `canary_runner.py` (khối chuẩn bị child environment), khi `m >= 200` hoặc `"Admin" in cluster`, BẮT BUỘC phải gán:
  ```python
  env["TAADAA_HOST_CONFIG"] = r"D:\Taadaa\machine-config\admin.yaml"
  env["ADB_SERVER_SOCKET"] = "tcp:192.168.110.119:5037"
  ```
  Nếu `m < 200`, trỏ về `kibe.yaml` và gỡ bỏ `ADB_SERVER_SOCKET`.

### G. Pitfall Timeout & Row Indexing Khi Canary Kiểm Chứng Luồng Login Recovery
- **Bẫy Timeout 300s cắt ngang recovery:**
  - Trong `feed_swipe_smoke.py`, timeout của `_run_fast_targeted_login()` là 420s, và `reconcile_timeout_seconds` là 600s.
  - Nếu Coordinator/Worker chạy lệnh `canary_runner.py` với `--timeout 300` (hoặc để mặc định 360s), lệnh sẽ bị timeout giả lập `[CANARY_TIMEOUT]` khi script đang giữa chừng login/reconcile trên thiết bị thật.
  - **Quy chuẩn:** Canary cho tác vụ nuôi feed có recovery tài khoản BẮT BUỘC đặt `--timeout >= 720` (khuyên dùng 900s) và chạy nền `terminal(background=True, notify_on_complete=True)`.
- **Bẫy Row Indexing đối soát tài khoản thật:**
  - Trong workbook, hàng tài khoản đầu tiên (slot 0) tương ứng với `--row 1` (`account_row_index=1`).
  - Nếu thiết bị đã có sẵn nick ở slot 0, chạy `--row 1` sẽ cho kết quả `already matched` và lướt feed ngay, KHÔNG hề kích hoạt nhánh `auto_login_recovery`.
  - Để tái hiện và kiểm chứng đúng nhánh tự login, BẮT BUỘC phải đối soát danh sách usable/workbook và truyền đúng `--row <N>` của tài khoản đang thực sự vắng mặt trên máy (ví dụ `--row 2` cho `thuthanh2911`).

### H. Đứt Gãy Luồng Recovery Tại Post-Session Upload-Hook (`multi_machine_feed_session.py`) — ĐÃ KHẮC PHỤC
- **Hiện tượng:** Khi máy kết thúc ca lướt feed và chuyển sang hook đăng video (`upload-hook`) gọi `scripts.tiktok_workflow`, Switcher không tìm thấy nick mục tiêu. State machine upload trả về `exit_code = 4` kèm `status = "LOGIN_RECOVERY_REQUIRED"` và `recovery_handler = "tiktok_login"`. Máy dừng hẳn mà không tự động mở flow đăng nhập TikTok.
- **Nguyên nhân gốc:**
  - Batch đăng video độc lập (`run_tiktok_upload_batch.ps1`) có code bắt Exit Code 4 để tự khởi chạy `Start-LoginRecoveryRunner` nạp nick rồi retry.
  - Trong khi đó, `upload-hook` chạy bên trong `multi_machine_feed_session.py` (dòng 4680–4705) khi nhận `is_success = False` chỉ ghi `upload_failed` và gửi `send_farm_machine_alert` ra ngoài, hoàn toàn thiếu nhánh hứng Exit Code 4 để kích hoạt `tiktok_login_v1.py` / `reconcile_tiktok_accounts.py`.
- **Kiến trúc đã triển khai (commit 81b202c):**
  - Trong `_run_upload_hook`: Bắt `proc.returncode == 4` và cờ `_upload_login_recovered`.
  - Thiết lập machine config cho child context: `child_ctx.config["_machine"] = account.machine`.
  - Kích hoạt `_maybe_recover_missing_account_via_login(child_ctx, account_id)` nạp bù nick vào Switcher.
  - Sau khi login thành công, retry lại lệnh upload `proc = subprocess.run(command, **subp_kwargs)` một lần duy nhất trước khi ghi nhận kết quả cuối cùng.

### I. Pitfall Floor Timeout của Worker Dispatch vs Terminal Foreground Timeout
- **Hiện tượng:** Khi Coordinator gọi `dispatch_worker.py` trong foreground qua `terminal(command=..., timeout=180)`, lệnh bị timeout ngắt ngang và Hermes chuyển sang trạng thái `[Orphan recovery]`.
- **Nguyên nhân gốc:** `dispatch_worker.py` có sàn timeout cứng cho Sol/Agy là `SOL_AGY_TIMEOUT_FLOOR = 480` (8 phút). Nếu terminal đặt `timeout=180`, process sẽ bị terminal hủy trước khi worker kịp hoàn thành hoặc fallback.
- **Quy tắc bắt buộc:** Khi gọi `dispatch_worker.py` hoặc các runner có worker AI, Coordinator BẮT BUỘC ép `timeout >= 480` (khuyên dùng 500s–600s), hoặc chạy ngầm `terminal(background=True, notify_on_complete=True)`. CẤM TUYỆT ĐỐI set timeout foreground 180s cho các lệnh gọi dispatch worker.

### J. Pitfall Canary Runner vs Live Batch Reservation Locks & Tính Chủ Động Sau Ca Chạy
- **Hiện tượng:** Khi chạy canary runner (`canary_runner.py --repo "tiktok-luot nuoi acc" --machine <N>`) để nghiệm thu sửa code trên máy thật, runner dừng ngay và báo lỗi: `multi-machine-feed-session: all machines were locked and skipped`.
- **Nguyên nhân gốc:** Thiết bị đang nằm trong phiên reservation lock của ca batch thật đang chạy ngầm (`command=run_tiktok.py --mode multi-machine-feed-session reservation`, `owner_active: true`, PID đang chạy). Theo cơ chế bulkhead bảo vệ farm, runner con sẽ không cướp lock thiết bị.
- **Quy chuẩn kiểm chứng (Offline/Mocked Invariant):**
  - Tuyệt đối không kill tiến trình batch hay xóa file lock của máy đang chạy ca thật chỉ để lấy kết quả canary.
  - Tuân thủ nghiêm ngặt Invariant L2: Nghiệm thu logic sửa đổi bằng bộ test suite focused mocked offline (`pytest python_runner/tests/test_upload_hook.py -q`), chạy trong < 10s để chứng minh tính đúng đắn trước khi commit.
- **Tính Chủ Động Canh Mở Khóa Sau Ca Chạy (Post-Shift Proactive Trigger):**
  - Ngay khi ca nuôi kết thúc (tiến trình batch giải phóng file lock `machine_<N>.lock.json`), Coordinator BẮT BUỘC chủ động poll trạng thái lock thiết bị và kích hoạt chạy Canary máy thật ngay lập tức, tuyệt đối KHÔNG ĐƯỢC đứng im chờ User phải giục (`Ủa nãy ca nuôi kết thúc r mày vẫn k làm à`).
  - Sau khi Canary hoàn tất thành công (Exit Code 0), lập tức soi mắt nghiệm thu ảnh qua WinRT OCR và gửi ảnh kèm `MEDIA:` báo cáo User dứt điểm.

## 3. Quy Trình Nạp Bù Tài Khoản Đúng Chuẩn (Actionable Reconcile Flow)
Để nạp nick còn thiếu vào slot trống của thiết bị mà không ảnh hưởng đến batch đang chạy:

1. **Sử dụng công cụ Reconcile chuyên dụng:**
   Script chuẩn: `D:/Taadaa/tiktok-log-in/scripts/reconcile_tiktok_accounts.py` (dùng engine `login_runner.account_reconcile` kết nối `Tiktok_Reg`).

2. **Cú pháp lệnh nạp bù 1 máy cụ thể (ví dụ M211 thiếu nick khanhcoi6114):**
   ```bash
   python D:/Taadaa/tiktok-log-in/scripts/reconcile_tiktok_accounts.py \
       --workbook "D:/OneDrive/TaadaaData/admin/taikhoan_run_safe.xlsx" \
       --machines 211 \
       --expected-username khanhcoi6114 \
       --adb-path "C:/Program Files (x86)/xiaowei/tools/adb.exe" \
       --login-project "D:/Taadaa/Tiktok_Reg" \
       --allow-live-reconcile
   ```

3. **Nguyên lý thực thi an toàn:**
   - Script tự động đối soát nick trong workbook với UI Switcher thực tế trên máy.
   - Bấm "Thêm tài khoản", thực hiện flow login có proxy xoay và giải mã IMAP OTP độc lập.
   - Sau khi login thành công, verify lại Switcher có đủ 8 slot trước khi nhả device lock.

## 4. Edge Cases Trong Flow Login Cần Xử Lý Tự Động (Pitfalls)

### A. Popup "Thêm số điện thoại" che khuất màn hình nhập Email (`fail_login_*_email_screen.xml`)
- **Hiện tượng:** Khi vừa chọn phương thức đăng nhập bằng Email/Username, TikTok có thể tự động bật bottom-sheet modal:
  - Header: `"Thêm số điện thoại"` / `"Thêm số điện thoại của bạn để tăng cường bảo mật..."`
  - Nút Đóng: `android.widget.Button` có `content-desc="Đóng"` hoặc `content-desc="Close"`, bounds điển hình `[936,861][1056,993]`.
- **Hậu quả nếu thiếu handler:** Hàm `fill_existing_email_and_continue()` trong `tiktok_login_v1.py` chờ text `"Email"` / `"TikTok ID"` nhưng bị popup che -> văng lỗi `RuntimeError: Khong thay man nhap email de login`.
- **Xử lý chuẩn:** Trong `fill_existing_email_and_continue()` trước khi tìm ô nhập email, bắt buộc kiểm tra sự hiện diện của text `"Thêm số điện thoại"` / `"Add phone number"` và tap vào nút Đóng (`content-desc="Đóng"` hoặc tọa độ tâm bounds) để đóng modal, sau đó tiếp tục điền email + password bình thường.

### B. Bug Nhận Diện Nhầm Nick Switcher Khi Trùng Tiền Tố Khác Số Đuôi (`matches_switcher_identity`)
- **Hiện tượng:** Máy chỉ có nick `khanhthu2275` nhưng ca chạy yêu cầu `khanhthu1609`. Switcher tap nhầm vào `khanhthu2275`, tưởng rằng đã switch thành công, lướt xong toàn bộ 16 video rồi đến cuối phiên mới báo lỗi `profile account mismatch`.
- **Nguyên nhân gốc:** Hàm `matches_switcher_identity` trong `automation_core.tiktok.account_switcher` sử dụng logic cắt bỏ số đuôi: `v1.rstrip("0123456789+ ") == v2.rstrip("0123456789+ ")`. Điều này làm `khanhthu2275` và `khanhthu1609` đều bị rút gọn thành `khanhthu`, khiến hệ thống phán đoán sai rằng đây là cùng một tài khoản.
- **Xử lý chuẩn:** Bổ sung điều kiện kiểm tra regex số đuôi (`re.search(r"\d+$", v)`). Nếu cả hai username đều có số đuôi mà số đuôi khác nhau (`2275 != 1609`), BẮT BUỘC trả về `False` ngay lập tức để runner nhận diện đúng tài khoản bị thiếu và kích hoạt auto-login recovery.

### C. Popup "Follow bạn bè của bạn" Che Màn Hình Profile Sau Khi Switch Nick
- **Hiện tượng:** Sau khi tap Switcher đổi nick thành công, TikTok bật modal/overlay toàn màn hình gợi ý *"Follow bạn bè của bạn"* / *"Follow lại"*. Màn hình này không có bottom navigation bar, khiến hàm phân loại `classify_screen` trả về `unknown TikTok state` và profile preflight bị đánh dấu `manual-needed` fail-closed.
- **Xử lý chuẩn:** Trong `_maybe_handle_profile_add_phone_guard`, tích hợp `find_matching_handler` bắt trúng `follow_friends_suggestion_popup` và gọi dismisser đóng lớp phủ bằng phím Back hoặc tap nút đóng trước khi đọc profile identity.

### D. Ép WinRT OCR Primary Cho Module Đăng Nhập (`social_reg_v1.py` / `tiktok_login_v1.py`)
- **Hiện tượng:** Khi chạy auto-login recovery trên dàn máy S7 cũ, thiết bị liên tục báo lỗi `atx-agent dump attempt failed`, timeout và sau đó rơi vào trạng thái `offline` hoặc ngắt kết nối USB vật lý.
- **Nguyên nhân:** Các script legacy gọi `get_ui_xml()` hàng chục lần để tìm nút và kiểm tra chữ. Thao tác dump XML bằng Java Accessibility Service trên Android vắt kiệt CPU Exynos 8890 (chạm 100%), khiến tiến trình bị kernel kill (`Killed 137`) và làm treo daemon `adbd` trên điện thoại.
- **Xử lý chuẩn:** Thay thế hoàn toàn các lệnh dump XML trong `find_text_tap` và `text_exists` sang **WinRT OCR Primary**:
  1. Chụp màn hình bằng native `screencap` về PC (0.1s).
  2. Dùng WinRT OCR trên CPU máy tính Windows bóc tách text và tọa độ hộp chữ `(x1, y1, x2, y2)`.
  3. Tap trực tiếp vào tọa độ tâm nút `(cx, cy)`.
  4. Chỉ fallback sang dump XML khi OCR thật sự không tìm thấy chữ trên ảnh.
  5. Đảm bảo tuân thủ `INVARIANT UI-OCR-1` và vượt qua kiểm tra của `python D:/Taadaa/tools/ui_policy_check.py`.


