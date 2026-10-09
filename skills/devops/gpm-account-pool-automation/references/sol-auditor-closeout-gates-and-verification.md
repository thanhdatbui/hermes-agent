# Sol Auditor Closeout Gates & Verification Patterns (GPM Auto)

Khi thực hiện task nghiệm thu/closeout hoặc giải quyết các finding từ Sol Auditor Scorecard trên repo `D:\Taadaa\GPM auto`, luôn tuân thủ các verification gates chính để đảm bảo điểm số >= 85/100 (APPROVED):

---

## Gate 1: Password Precedence (`OVERRIDE_PASSWORD`)
Trong quy trình xác thực OAuth / 2FA (`scripts/run_oauth_s7_pipeline.py`), logic xác định mật khẩu phải tuân theo thứ tự ưu tiên 3 tầng:
```python
password = os.environ.get("OVERRIDE_PASSWORD") or creds.get("password") or acc.get("password", "")
```
- **Tầng 1 (Cao nhất)**: `os.environ.get("OVERRIDE_PASSWORD")` — cho phép inject mật khẩu khẩn cấp hoặc mật khẩu dùng chung qua biến môi trường mà không cần sửa file Excel/DB.
- **Tầng 2**: `creds.get("password")` — lấy từ file quản lý tập trung (`master_gmail_manager.xlsx`).
- **Tầng 3 (Fallback)**: `acc.get("password", "")` — lấy trực tiếp từ dữ liệu profile GPM.

Khi viết unit test cho Gate 1:
- Dùng `unittest.mock.patch.dict(os.environ, ...)` và `patch.object(pipeline, "get_creds", ...)`.
- Kiểm tra cả 3 trường hợp: có env var ghi đè, không có env var (nhận từ creds), và creds rỗng (fallback acc).

---

## Gate 2: Logging Hygiene & Anti-Cron Alert Spam
Trong các runner chạy nền/cronjob (`scripts/preflight_s7_rolling_cleanup.py`, `scripts/run_add_2fa_remaining.py`):
- **Tuyệt đối không gắn `StreamHandler(sys.stdout)` ở root/module level**, vì toàn bộ stdout sẽ bị cronjob bắt lại và kích hoạt telegram spam / false alarm.
- Module logger phải set:
  ```python
  logger = logging.getLogger("<Name>")
  logger.propagate = False
  ```
- Handlers mặc định chỉ dùng `logging.FileHandler(..., encoding="utf-8")`.
- Nếu có CLI entrypoint (`if __name__ == '__main__':` hoặc hàm `main()`), chỉ stream log ra `sys.stderr` khi chạy tương tác.

Khi viết unit test cho Gate 2:
- Kiểm tra `logger.propagate is False`.
- Duyệt qua `logger.handlers` và `logging.getLogger().handlers` để khẳng định không có `StreamHandler` nào trỏ tới `sys.stdout`.

---

## Gate 3: Schema Validation `config/oauth_pipeline_status.json`
Trạng thái pipeline OAuth được lưu trữ tại `config/oauth_pipeline_status.json`:
- Dictionary chính chứa các tài khoản kết nối thành công: `omniroute_success` (hoặc alias `live_accounts`).
- Mỗi entry tài khoản phải đảm bảo 4 thuộc tính bắt buộc:
  - `machine`: `int` (ID máy Farm)
  - `port`: `int` (Port CDP / proxy)
  - `connection_id`: `str` (UUID > 10 ký tự kết nối OmniRoute)
  - `status`: `"HTTP_200_OK"`

File test nghiệm thu chuẩn được đặt tại `tests/test_closeout_gates.py`.

---

## Gate 4: Test Parity / Focused Test Mapping (Bẫy Lệch Tỷ Lệ Diff vs Test Evidence)
Khi commit chứa thay đổi trên nhiều file mã nguồn (`src/<stem>.py`, `scripts/<stem>.py`):
Sol Auditor sẽ **TRỪ NẶNG ĐIỂM** `Test Evidence` và `Farm Safety` (tụt xuống 74 - 78/100, REJECTED) nếu phát hiện file mã nguồn trong diff không có unit test chứng minh tương ứng!

### Cơ chế của `closeout_gate.py`:
- `closeout_gate.py` tự động phát hiện focused test dựa trên danh sách staged/committed files:
  ```python
  direct_tests = [f for f in staged_files if ('tests/' in f or 'test/' in f) and f.endswith('.py')]
  if direct_tests:
      focused = direct_tests
  ```
- **BẪY NGUY HIỂM**: Nếu commit chứa nhiều file source nhưng chỉ chứa 1 file test trực tiếp (ví dụ `tests/test_gpm_client.py`), `closeout_gate` sẽ **CHỈ CHẠY 1 FILE TEST ĐÓ** và bỏ qua toàn bộ test của các file source khác!
- Hậu quả: Reviewer nhận thấy diff chạm vào 5-6 files nhưng chỉ chạy test 1 file -> Đánh giá "chưa có test cho các luồng đã sửa, phạm vi sửa lớn hơn phạm vi test" -> REJECT.

### Quy tắc Vàng để đạt >= 85/100:
1. **1-to-1 Test Mapping**: Mọi file mã nguồn được sửa hoặc thêm mới trong commit BẮT BUỘC phải đi kèm file test tương ứng trong cùng commit:
   - `scripts/run_add_2fa_remaining.py` ➔ `tests/test_run_add_2fa_remaining.py`
   - `scripts/run_oauth_s7_pipeline.py` ➔ `tests/test_run_oauth_s7_pipeline.py`
   - `src/codex_omniroute_hook.py` ➔ `tests/test_codex_omniroute_hook.py`
   - `src/gpm_client.py` ➔ `tests/test_gpm_client.py`
2. **Không đưa script lớn chưa hoàn thiện vào commit**: Tuyệt đối không commit các file script mới dài hàng trăm dòng (như `batch_dual_oauth_5workers.py`) khi chưa có test suite hoàn chỉnh đi kèm. Dùng `git rm --cached <script>` để loại bỏ khỏi commit, giữ diff tinh gọn và 100% được bao phủ bởi test.

---

## Gate 5: Process Cleanup & Chrome Isolation Test Mocking
Khi viết test cho cơ chế dọn dẹp tiến trình và bảo vệ Google Chrome cá nhân:
1. **Assert Chrome cá nhân không bị kill**:
   ```python
   p_personal = MagicMock()
   p_personal.info = {"pid": 1111, "name": "chrome.exe", "cmdline": [r"C:\Program Files\Google\Chrome\Application\chrome.exe"]}
   p_gpm = MagicMock()
   p_gpm.info = {"pid": 2222, "name": "chrome.exe", "cmdline": [r"C:\Users\...\GPMLogin\gpm_browser\chrome.exe", "--remote-debugging-port=40444"]}
   mock_psutil.process_iter.return_value = [p_personal, p_gpm]

   res = client.stop_profile("test-uuid-1234", remote_port=40444)
   p_personal.terminate.assert_not_called()
   p_gpm.terminate.assert_called_once()
   ```
2. **Mock `get_profile` khi test Endpoint Fallback**:
   Trong `stop_profile`, hàm sẽ gọi `self.get_profile(profile_id)` trước để lấy `profile_path`. Do đó khi test fallback 2 endpoint `/close` và `/stop`, bắt buộc phải:
   ```python
   with patch.object(client, "get_profile", return_value=None), patch("requests.get") as mock_get:
       mock_get.side_effect = [mock_res_fail, mock_res_ok]
       res = client.stop_profile("test-uuid-1234")
       assert mock_get.call_count == 2
   ```

---

## Gate 6: Bash Quoting Trap với PowerShell CIM Query
Khi chạy lệnh PowerShell thông qua terminal Git-Bash trên Windows:
- Ký tự `$_` trong PowerShell (ví dụ `Where-Object { $_.CommandLine -like ... }`) **trùng với biến đặc biệt của Bash** (lưu argument cuối cùng của lệnh trước đó).
- Nếu bao bọc bởi dấu ngoặc kép `"powershell -Command "..."`, Bash sẽ ngầm thế chỗ `$_` thành chuỗi đường dẫn trước đó (như `/c/Users/Kibe`), sinh ra lỗi cú pháp hàng loạt: `The term '/c/Users/Kibe.CommandLine' is not recognized`.
- **CÁCH KHẮC PHỤC**:
  - Luôn escape ký tự `$` thành `\$_.CommandLine` trong bash string:
    ```bash
    powershell -Command "Get-CimInstance Win32_Process | Where-Object { \$_.CommandLine -like '*GPMLogin*' } | ..."
    ```
  - Hoặc trong Python subprocess, truyền dạng mảng args không qua bash shell (`shell=False`):
    ```python
    subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True)
    ```
