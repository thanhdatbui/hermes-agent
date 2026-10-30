# Zero-Token Cron Watchdog Wrapper & Pre-Tool Hook Wiring

## 1. Bản Chất Sự Cố LLM Token Bloat & HTTP 503 Ban Đêm
- Khi tạo cron job theo dõi (watchdog), nếu agent viết dạng `prompt="..."` mà không gán `no_agent: true`, Hermes scheduler sẽ tự động khởi tạo subagent AI mới mỗi tick.
- Mỗi tick, subagent kéo toàn bộ System Prompt (context ~8k–43k tokens) bắn lên upstream LLM proxy (OmniRoute / Gemini / Claude).
- Khi chạy liên tục nhiều chu kỳ (10–30 phút/lần) trong đêm:
  1. Gây cạn kiệt Token Per Minute (TPM).
  2. Khi proxy quá tải/rớt mạng, upstream trả về `HTTP 503: Service temporarily unavailable: all targets were skipped by pre-dispatch filters`.
  3. Khi phiên chat chính thức thức dậy với context phình to (150k+ tokens), request lập tức dính 429/503/timeout.

## 2. Quy Chuẩn Đường Dẫn Tương Đối Của Hermes Cron
- Hermes Cron Runner bắt buộc tham số `script` phải là tên file tương đối nằm trong `~/.hermes/scripts/` (hoặc `%LOCALAPPDATA%\hermes\scripts\`).
- Nếu truyền đường dẫn tuyệt đối như `D:/Taadaa/orders/watch_jt_delivery.py`, scheduler sẽ ném lỗi:
  `Script path must be relative to ~/.hermes/scripts/. Got absolute or home-relative path: 'D:\Taadaa\orders\watch_jt_delivery.py'`.

## 3. Workflow Tạo Zero-Token Watchdog Chuẩn Cho Repo Ngoài
1. **Viết wrapper script tại repo Deploy:**
   Tạo file `D:\Taadaa\Hermes\deploy\hermes-home\scripts\<script_name>.py`.
   Wrapper sử dụng `subprocess.run` gọi script nghiệp vụ thực tế với `cwd` trỏ về repo tương ứng.
   Tuân thủ watchdog pattern:
   - Nếu không có biến động/sự kiện mới: stdout rỗng (`sys.exit(0)`). Hermes im lặng 100%, không gửi tin nhắn rác.
   - Nếu có sự kiện mới/cần cảnh báo: in ra stdout (`print(...)`), Hermes tự động chuyển phát nguyên văn stdout sang channel đích.
2. **Kích hoạt đồng bộ sang Runtime & OneDrive:**
   Chạy `python D:/Taadaa/Hermes/deploy/hermes-home/scripts/cron_sync_watchdog.py`.
   Script tự động copy sang `%LOCALAPPDATA%\hermes\scripts\` và `OneDrive Taadaa_Sync_Shared`.
3. **Đăng ký Cron Job:**
   Gọi tool `cronjob` với:
   - `action="create"` (hoặc `"update"`)
   - `no_agent=True`
   - `script="<script_name>.py"`
   - `workdir="<path_repo>"`
   - `deliver="telegram:<channel_id>"` (tra cứu Chat ID từ `$LOCALAPPDATA/hermes/channel_directory.json`).

## 4. Anti-Kneejerk Deletion & Quy Trình 3 Bước Remediate Cron Lỗi Timeout
- Khi cron job gặp lỗi 503 hoặc "provider timeout. Fallback chain was exhausted or unavailable":
  * CẤM xóa job nếu nghiệp vụ/đơn hàng/tác vụ nền vẫn đang hoạt động.
  * Nguyên nhân: Job có `script` nhưng thiếu `no_agent: true`, khiến scheduler kích hoạt subagent LLM và timeout khi proxy upstream quá tải.
- **Quy trình 3 bước Remediate khép kín:**
  1. **Update cấu hình:** Gọi `cronjob(action='update', job_id='<id>', no_agent=True)` để tắt hoàn toàn LLM subagent.
  2. **Đồng bộ 3 điểm:** Chạy `python D:/Taadaa/Hermes/deploy/hermes-home/scripts/cron_sync_watchdog.py` để cập nhật `jobs.json` đồng thời tại Runtime, Deploy repo (`D:\Taadaa\Hermes\deploy\hermes-home\cron\jobs.json`) và OneDrive Shared.
  3. **Kiểm chứng chạy ngay:** Kích hoạt `cronjob(action='run', job_id='<id>')`, xác nhận kết quả trả về `execution_success: true` và `last_status: 'ok'`.

## 5. Đồng Bộ 9 Pre-Tool Hooks Bắt Buộc (Runtime ↔ Deploy Parity)
Cả `%LOCALAPPDATA%\hermes\config.yaml` và `D:\Taadaa\Hermes\deploy\hermes-home\config.yaml` bắt buộc phải nạp đủ 9 pre-tool hooks để bảo vệ cơ học, chống agent vi phạm rule:
1. `guard_read_file_size.py` (`read_file`): Chặn đọc file quá lớn.
2. `guard_broad_grep.py` (`terminal|search_files`): Chặn quét ổ đĩa diện rộng (`grep -r`, `find`, `search_files`).
3. `guard_device_bulkhead.py` (`terminal`): Giới hạn can thiệp ADB, bảo vệ máy farm.
4. `guard_dispatch_contract.py` (`delegate_task`): Ép hợp đồng O(1) và fail-fast khi gọi worker.
5. `guard_closeout_discipline.py` (`terminal|clarify`): Cấm git push lậu và cấm clarify trốn việc.
6. `guard_cronjob_safety.py` (`cronjob|terminal`): **Bắt buộc `no_agent=true`** & ép `CREATE_NO_WINDOW (0x08000000)` ẩn console.
7. `guard_android_proxy.py` (`terminal`): **Bắt buộc IP tĩnh LAN RFC1918** khi gán proxy Android.
8. `guard_pytest_scope.py` (`terminal`): Buộc chạy focused test, cấm quét cả repo.
9. `guard_model_drift.py` (`terminal`): Chặn truyền model cấm (sol-pro, sol-instant) vào closeout_gate.

## 6. Cạm Bẫy Mất Cờ `no_agent: true` Khi Update và Lỗ Hổng Gate Kiểm Tra
- **Bẫy Hermes Cron Update (`no_agent` Default False):** Khi gọi `cronjob(action='update', ...)` để sửa bất kỳ trường nào (như `schedule`, `prompt`, `workdir`), nếu không truyền tường minh `no_agent=True`, runtime Hermes tự động gán mặc định `no_agent=False`. Điều này âm thầm tước bỏ chế độ pure script và kích hoạt lại LLM subagent, dẫn đến provider timeout khi proxy upstream quá tải.
  👉 **Quy tắc bất biến:** Mọi lời gọi `cronjob(action='update')` BẮT BUỘC phải luôn truyền kèm `no_agent=True`.
- **Lỗ hổng Blind-Spot của Gate tiền kiểm (`if "no_agent" in ti`):**
  Trong `guard_cronjob_safety.py`, câu lệnh kiểm tra:
  ```python
  if "no_agent" in ti and ti["no_agent"] is not True:
      deny_cron_policy(...)
  ```
  chỉ chặn khi tham số update có chứa key `"no_agent"`. Khi Agent gọi update chỉ truyền `job_id` và `schedule`, điều kiện `if "no_agent" in ti` trả về `False` khiến Gate bị lọt qua hoàn toàn.
  👉 **Thiết kế Gate chuẩn:** Bắt buộc phải kiểm tra `if ti.get("no_agent") is not True:` để chặn đứng mọi lời gọi `update` thiếu cờ `no_agent=True`.
