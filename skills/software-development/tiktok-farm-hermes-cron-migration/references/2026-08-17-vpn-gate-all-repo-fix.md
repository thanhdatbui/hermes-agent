# VPN gate all-repo fix (2026-08-17) — hướng A hoàn tất

## Vấn đề
`"máy không VPN vẫn được phép chạy"` (user phát hiện). Root cause: mọi consumer repo
hardcode `DEFAULT_PROXY_MAPPING = kibe\PROXYgandienthoai.xlsx` → trên host admin
(máy 200+) serial không có trong mapping kibe → `required=False` → VPN gate bị bỏ qua.

## User chốt semantics (QUAN TRỌNG — đọc trước khi sửa core)
1. "Máy CÓ map vpn mới bắt buộc vpn. Máy k map thì kệ nó cho chạy direct bth"
   → **GIỮ mapping-exemption** cho máy unmapped (KHÔNG đổi `check_android_vpn if not required: return allowed`).
2. "Không bật vpn thì không được chạy" — cho máy mapped.
3. "Phải reboot để cho gan proxy thử bật vpn (reboot 1-2 lần tránh loop lỗi do gan proxy) rồi mới cho chạy"
   → recovery: GanProxy reassign → soft-reboot → verify → vẫn fail mới block.
4. User cho phép tự làm ("k thì tự làm") — KHÔNG cần plan/audit cho fix này.

## Implementation hoàn tất (commits)
- **Core `automation_core 0.4.46` (commit `2db001e`)** — `src/automation_core/preflight.py`:
  `resolve_proxy_mapping_path(env=None, *, filename="PROXYgandienthoai.xlsx")`:
  - `TAADAA_HOST_CONFIG` set → đọc yaml → `workbook_root / filename`; thiếu file → raise
    `ConsumerPreflightError("proxy mapping workbook missing for host")`; thiếu root → raise.
  - Không host config → env `AUTOMATION_PROXY_MAPPING`/`TIKTOK_PROXY_MAPPING` (file phải tồn tại);
    không gì → raise `proxy mapping workbook unresolved`.
  - KHÔNG fallback kibe — đó chính là bug cũ.
- **Repo nuôi acc `vpn_preflight.py` (commit `9bfec1e`)**:
  - `_resolve_proxy_mapping()` → gọi `resolve_proxy_mapping_path()`.
  - `require_vichanger_connected(adb_path, serial, *, recover=True)`:
    - `serial_is_mapped_in_workbook` → unmapped: `require_android_vpn(required=False)` (direct, không check).
    - mapped: `require_android_vpn(required=True)`; fail → `recover_missing_android_vpn(adb, serial,
      live_vpn_verifier=lambda s: _vpn_up(adb))`; recovery fail → wrap `ConsumerPreflightError`; recovery OK
      → `require_android_vpn` lại lần cuối → fail nữa mới raise.
  - `_vpn_up(adb)` = `check_android_vpn(adb, required=True).allowed` (live verifier cho recovery loop).
- **tiktok-log-in + tiktok-add-bao-mat** (mỗi repo 1 commit): thay hardcode bằng `_resolve_proxy_mapping()`
  (cùng pattern — có thể copy-paste script patch, old/new block giống hệt 3 nơi).

## Quy trình patch all-repo (đã dùng, tái sử dụng được)
1. Grep `grep -rlnE "DEFAULT_PROXY_MAPPING|require_vichanger_connected|require_android_vpn" /d/Taadaa/*/` để
   có danh sách repo đích — đừng đoán.
2. Viết 1 script patch với OLD/NEW block chung, chạy cho N repo, `py_compile` từng file.
3. Smoke import từng repo: `PYTHONPATH="" python -c "from <module> import DEFAULT_PROXY_MAPPING"` → in path
   phải là host KIBE (không phải fallback).
4. Chạy test đích: core `test_preflight` + `test_device_recovery`; consumer `-k "vpn or mapping"`;
   mỗi repo 1 suite liên quan.
5. Bump core version + build wheel (`python -m build --wheel`) + cài VÀO CẢ 2 env:
   automation (`D:\Taadaa\python-envs\automation`) VÀ Python312 (`C:\Users\Kibe\AppData\Local\Programs\Python\Python312`)
   — Task Scheduler bare `python` resolve về Python312.
   **BẪY pip cache**: lần đầu `pip install --force-reinstall` (không `--no-cache-dir`) vẫn báo
   `Successfully installed` nhưng `importlib.metadata.version` vẫn 0.4.45 → phải thêm `--no-cache-dir`.
6. Commit riêng từng repo với message mô tả bug + fix.

## Verify evidence (số thật)
- kibe farm: 80/80 serial có trong PROXYgandienthoai.xlsx → tất cả bắt buộc VPN.
- admin farm: `D:\OneDrive\TaadaaData\admin\` TRỐNG (chưa có PROXY file) → host admin giờ RAISE khi
  resolve mapping (fail-closed) thay vì exempt im lặng. Muốn admin chạy phải tạo file mapping riêng
  (không tự tạo — hỏi user).
- Core 0.4.46: `test_preflight.py` 7 passed, `test_device_recovery.py` 47 passed.
- Consumer: `-k "vpn or mapping"` 2 passed; tiktok-log-in 29 passed; add-bao-mat 18 passed.

## ĐỢT 2 — final all-repo sweep (17/08 tối, sau khi user hỏi "áp dụng all repo chưa")

Scan phát hiện: `grep -rln "OneDrive.TaadaaData.kibe.PROXYgandienthoai" --include=*.py /d/Taadaa`
(loại `venv|site-packages|__pycache__|.git|build/|dist/|automation-core|node_modules|.bak|context-worktrees|jitter-backup|gmail-jitter-backup|.ai-runs|tests/`).

Các repo còn hardcode kibe → patched:
- `add mail khoi phuc/run_add_recovery.py` (git repo → commit; **sửa cả nhận định cũ "không đụng"** — thực tế CÓ hardcode).
- `register gmail/gmail_reg_v10.py` + `guarded_device_reboot.py` — **KHÔNG phải git repo** → patch trực tiếp file, không commit được.
- `Hotmail/flows/hotmail_login.py` — non-git; ⚠️ cảnh báo sibling subagent đang sửa file này → đọc lại trước write.
- `gan-proxy/scripts/gan_proxy_fleet.py` — chain `GAN_PROXY_MAPPING → AUTOMATION_PROXY_MAPPING → TIKTOK_PROXY_MAPPING → resolve_proxy_mapping_path()`.
- worktree `tiktok-log-in-recovery-adapter-p2-wt/login_runner/cli.py` — git worktree nhánh `recovery-adapter/login-p2` → patch + commit RIÊNG (không nhầm với repo main; `git worktree list` để xác định).

**Pattern patch repo non-git / worktree** (không cần sửa import block):
`str(__import__("automation_core.preflight", fromlist=["resolve_proxy_mapping_path"]).resolve_proxy_mapping_path())`

**LOẠI TRỪ đúng (KHÔNG patch)**: `Tiktok_Reg` — chỉ comment "synced from PROXYgandienthoai.xlsx" +
`PROXY_MAP_PATH = D:\PROXYgandienthoai.xlsx` (device-map file riêng, không phải VPN gate runtime —
social_reg_v1.py không gọi `require_android_vpn`); `gan-proxy/tests` (test fixture có hardcode — không đụng);
backups/`jitter-backup`/`gmail-jitter-backup`/`context-worktrees` (không active).

**Verify cuối**: chạy LẠI scan → 0 file runtime còn hardcode; mỗi file patched `py_compile` OK;
repo git có commit message `fix(vpn): host-aware proxy-mapping resolution (fail-closed, no kibe fallback)`.

## CÒN DỞ (session kế check)
- hermes venv vẫn automation_core 0.4.43 — nếu feed stream qua PowerShell bare-python resolve hermes venv
  (PATH HKCU) → cài 0.4.46 vào hermes venv hoặc sửa `run-feed-session.ps1` default `$Python`.
- Cron job `reap-dead-owner-locks` (LLM-driven) vẫn `last_status: error` 401 — chưa chuyển no_agent
  (chờ user duyệt).
- Ví dụ rule "không VPN không chạy" hiện nằm ở CONSUMER (vpn_preflight) + core resolver — nếu repo khác
  vẫn gọi `require_android_vpn` trực tiếp (gmail-jitter) thì chỉ được fail-closed resolve, chưa có
  recovery — xem xét nếu user yêu cầu all-repo recovery.