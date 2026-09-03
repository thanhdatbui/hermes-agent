# Live-wire activation permit — recipe chi tiết (2026-08-17 tối)

Context: hoàn tất live-wiring 3 cron phase9 (picker/runner/watcher) sau khi staging
đã tạo job paused. Vấn đề gốc: **Hermes cron tool (`cronjob`) KHÔNG có field env** —
không thể set `HERMES_CRON_PICKER_ENABLED=1` cho job. Wrapper default-off (chỉ active
khi env `HERMES_CRON_*_ENABLED=1` hoặc `HERMES_CRON_PERMIT_FILE`) sẽ LUÔN exit 0 im
lặng qua cron thật → cron "chạy" nhưng không làm gì.

## Kiến trúc activation (3 wrapper `scripts/hermes_cron/tiktok_{picker,runner,watcher}.py`)

`is_activated(env)` fallback chain:
1. `HERMES_CRON_<KIND>_ENABLED == "1"` (env — giữ cho test/CLI thủ công)
2. `HERMES_CRON_PERMIT_FILE` env → path (regular, non-symlink)
3. `_default_permit_file()` = `repo_root() / "runtime" / "hermes-cron" / "permits" / f"{Path(__file__).stem}.permit"`

`repo_root()` walk lên tìm `.git` từ `__file__` — wrapper trong repo nên luôn resolve
đúng. Test `test_wrapper_default_off_without_valid_activation_marker_or_permit` +
`test_wrapper_default_off_has_empty_stdout_exit_zero_and_no_child` vẫn pass vì permit
file chưa tồn tại khi test chạy.

## Config: `runtime/hermes-cron/env.json`

Wrapper `main()` đổi `env = os.environ` → `env = merged_env(os.environ)`:
- `repo_env_overrides()`: đọc `repo_root()/runtime/hermes-cron/env.json` (bỏ qua
  symlink/parse lỗi/non-dict) → dict[str, str]
- `merged_env`: `merged = dict(env)` rồi `setdefault` từ overrides → **process env THẮNG**

Required keys per wrapper (fail-closed exit 3 nếu thiếu sau merge):
- picker: `STATE_ROOT, SOURCE_CONFIG, FEED_STATE_JSON, POST_STATE_JSON, OFFLINE_ROOT, OWNER_ID, WORKER_ID`
- runner: `STATE_ROOT, SOURCE_CONFIG, OFFLINE_ROOT` (+ optional `REPO, FEED_WORKBOOK`)
- watcher: `STATE_ROOT, SOURCE_CONFIG, OFFLINE_ROOT, REPORT_JSONL`

File chỉ do operator tạo lúc approve. **BẪY TEST**: nếu để sót `env.json` trong repo,
các wrapper test spawn child thật → fail hàng loạt (`test_wrapper_spawns_child_*`).
Sau E2E phải `rm -f runtime/hermes-cron/env.json runtime/hermes-cron/permits/*.permit`.

## Runner execute gate (`python_runner/scripts/hermes_cron_runner.py`)

- `_runner_live_permit()`: `here.parents[2]` (python_runner/scripts → repo root) +
  `runtime/hermes-cron/permits/tiktok_runner.permit` — regular, non-symlink.
- Gate: `if args.execute or args.repo or args.feed_workbook: if not _live_permit:
  parser.error("offline harness refuses ...")` — offline KHÔNG đổi hành vi.
- Adapter: `live = _live_permit is not None`; `enabled=live`; repo/workbook từ args
  hoặc default offline; `run_entry(..., execute=live)`.
- Wrapper runner `ALLOWED_FORWARD_ENV` + `_ARG_MAP` thêm
  `HERMES_CRON_REPO → --repo`, `HERMES_CRON_FEED_WORKBOOK → --feed-workbook`.

## BẪY MSYS path + None return (bug thật, 2 lớp)

1. `TARGET_PYTHON_DEFAULT = "/d/Taadaa/python-envs/automation/Scripts/python.exe"`
   (MSYS). Windows `subprocess.run` → `CreateProcess` không hiểu `/d/` →
   `FileNotFoundError: [WinError 2]`. Test wrapper fake python path là Windows
   (`C:\...Temp\...\fake_python.cmd`) → KHÔNG lộ trong pytest; chỉ lộ khi E2E
   wrapper thật với permit+env.json.
   Fix `target_python()`:
   ```python
   value = os.environ.get(TARGET_PYTHON_ENV) or TARGET_PYTHON_DEFAULT
   if value.startswith("/") and len(value) > 2 and value[2] == "/":
       drive = f"{value[1].upper()}:"
       rest = value[3:].replace("/", "\\")
       return drive + "\\" + rest
   return value
   ```
2. **BẪY patch tool**: sửa indentation bằng patch dễ để `return value` lọt VÀO trong
   `if` (8 spaces) → hàm không return khi path không bắt đầu `/` → trả `None` →
   `subprocess` `list2cmdline` → `TypeError: expected str, bytes or os.PathLike
   object, not NoneType` (traceback gốc `<frozen os>`, line 859, `fsdecode`).
   Chẩn đoán: in `child_argv[0]` trước spawn — `None` = thiếu return ở mức function.
   Sau mọi patch: `py_compile` từng file + chạy E2E wrapper thật.

## E2E mô phỏng cron thật (cách verify đúng)

```bash
# 1. tạo permit + env.json (nội dung như operator sẽ tạo lúc approve)
echo "test-activation" > runtime/hermes-cron/permits/tiktok_picker.permit
cat > runtime/hermes-cron/env.json <<'EOF'
{ "HERMES_CRON_STATE_ROOT": "D:/Taadaa/runtime/kibe/cron-state",
  "HERMES_CRON_SOURCE_CONFIG": "D:/Taadaa/runtime/kibe/cron-source/hermes_cron_source_config.json",
  "HERMES_CRON_OFFLINE_ROOT": "D:/Taadaa/runtime/kibe/cron-offline",
  "HERMES_CRON_OWNER_ID": "hermes-cron-kibe",
  "HERMES_CRON_WORKER_ID": "picker-worker",
  "HERMES_CRON_FEED_STATE_JSON": "D:/Taadaa/runtime/kibe/cron-state/feed_state.json",
  "HERMES_CRON_POST_STATE_JSON": "D:/Taadaa/runtime/kibe/cron-state/post_state.json",
  "HERMES_CRON_REPORT_JSONL": "D:/Taadaa/runtime/kibe/cron-state/report.jsonl",
  "HERMES_CRON_REPO": "D:/Taadaa/tiktok-luot nuoi acc",
  "HERMES_CRON_FEED_WORKBOOK": "D:/OneDrive/TaadaaData/kibe/taikhoan_run_safe.xlsx" }
EOF
# 2. chạy wrapper (KHÔNG set env HERMES_CRON_* — mô phỏng cron thật)
PYTHONPATH="" timeout 90 .../python.exe -B scripts/hermes_cron/tiktok_picker.py
# 3. kỳ vọng: spawn child đúng python D:\..., fail chỉ vì source config chưa generate
#    (exit 1 CalledProcessError từ child = ĐÚNG — chuỗi live hoạt động)
# 4. DỌN: rm -f runtime/hermes-cron/env.json runtime/hermes-cron/permits/*.permit
```

## Bật checklist (khi user duyệt resume)

1. Generate `hermes_cron_source_config.json`: `scripts/generate_cron_source_config.py`
   cần 3 input:
   - safe projection (JSON `{schema_version:1, projection:"safe-v1", rows:[{account_id,
     machine, serial, row, target_count?, video_available?}]}`) — build từ
     `taikhoan_run_safe.xlsx` (480 rows, máy 1-80, 6 slot/máy)
   - assignment manifest THẬT: `%LOCALAPPDATA%\automation-core\assignments\tiktok-feed.json`
     (schema_version 1, 74 máy 1-74, resources `machine:N`)
   - journal facts (canonical, revision = sha256 content-derived)
2. Tạo `env.json` + 3 permit files (`tiktok_picker.permit`, `tiktok_runner.permit`,
   `tiktok_watcher.permit`)
3. Resume 3 job (picker `0 6 * * *`, runner `*/15 * * * *`, watcher `7,22,37,52 * * * *`)
4. Verify: `cronjob action=run` từng job → `last_status` không error

## Xung đột data đang mở — slot không liên tục (chờ user chốt A/B)

Generator `_read_safe_projection` yêu cầu `sorted(slots) == list(range(1, N+1))`
(physical slots liên tục từ 1). Workbook thật có 8 máy vi phạm:
**22, 33, 34, 39, 40, 53, 61, 66** — acc ở hàng 1,2,4 (hàng 3 trống) do nguồn
`taikhoan_dat_v2` có ô trống giữa.

- A) Nén acc về đầu (chạy sync-safe-workbook nén) → ĐỔI row mapping acc → rủi ro lệch
  Tik1/Tik2/Tik3 workbook theo row.
- B) Giữ row vật lý, sửa generator cho phép slot gián đoạn (accept 1,2,4) → an toàn
  mapping, chỉ đổi 1 ràng buộc code cron. **Nghiêng B** (không đụng data cũ).

## MaxWorkers = 30

`run-feed-session.ps1` param `[int]$MaxWorkers = 40` → `30` (user: "đã đc chứng minh
30 vẫn ổn"). Verify parse không chạy:
`powershell -NoProfile -Command "$t = [System.Management.Automation.Language.Parser]::ParseFile('...ps1', [ref]$null, [ref]$err); if ($err.Count) {...} else {'PS PARSE OK'}"`.

## Trạng thái sau session (17/08 tối)

- Commits: `5e35ee9` (runner execute gate + permit activation + staging schedule
  normalize), tiếp theo commit env.json fallback + CreateProcess fix (137 insertions,
  3 files). 216 tests pass (contract/integration/p1_r2/wrappers/staging).
- 3 job cron vẫn PAUSED — resume chỉ khi user duyệt.
- `reap-dead-owner-locks` đã chuyển no_agent script-only (`last_status: ok`).
