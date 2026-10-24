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

## 4. Anti-Kneejerk Deletion (Cấm Xóa Vội Vã Khi Gặp Lỗi)
- Khi cron job gặp lỗi 503 hoặc timeout, CẤM xóa job nếu đơn hàng/tác vụ nền vẫn đang hoạt động (ví dụ: đơn hàng còn đang trung chuyển, chưa giao).
- BẮT BUỘC sửa lại (remediate) cấu hình thành pure script `no_agent: true`.

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
