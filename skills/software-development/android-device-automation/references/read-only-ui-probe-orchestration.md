# Read-only UI probe orchestration (tiktok-follow, mode2 selector calibration)

Recipe đã chạy live 2026-08-12 (máy 1, serial hash `2b8f46746584`) — probe
read-only + đúng 1 lần launch do user authorize. Khác biệt so với section
"Read-only probe orchestration" trong SKILL.md: ở đây target đã cố định
(máy 1) chứ không chọn máy đầu tiên pass; launch TikTok được phép ĐÚNG MỘT lần.

## Thứ tự bắt buộc (đã verify live)

1. **Đọc context**: `AGENTS.md` → `PROJECT_RULES.md` → `HANDOFF.md` + probe tool
   hiện hành (`tools/dump_selectors.py` — chỉ đọc, có sẵn guard token destructive).
2. **Resolve máy → serial** từ safe workbook
   `D:\OneDrive\TaadaaData\kibe\taikhoan_run_safe.xlsx` (header `may, device id, id`):
   chỉ đọc cột mapping, in serial hash (SHA-256 8-12 hex), KHÔNG đọc/in cột `id`
   (credential). Nếu 1 máy resolve ra >1 serial khác nhau → BLOCKER.
3. **Preflight checks (trước bất kỳ device action)**:
   - `adb devices` → serial có online không.
   - Lock store `C:\Users\Kibe\.codex\device-locks`: scan `machine_<N>` +
     `serial_<S>` lock; `owner_active=true` + PID còn sống (verify qua
     `wmic process where "ProcessId=N" get ProcessId`) → DEFERRED_LOCKED, skip.
   - Process bận: `wmic process where "name='python.exe'" get ProcessId,CommandLine`
     → regex `tiktok_workflow` + `--machine N` (consumer đăng video KHÔNG ghi lock
     store — pitfall PROJECT_RULES).
4. **Acquire lock** `automation_core.device_lock.acquire_device_lock(...,
   bypass_proxy_readiness=True)` (tránh stall 180s `wait_for_proxy_ready`),
   project=tên consumer.
5. **VPN preflight NGAY sau lock** (ordering bắt buộc): non-raising
   `check_android_vpn(adb, required=serial_is_mapped_in_workbook(PROXY, serial,
   serial_headers=("phoneId","deviceId","serial")))` — ghi evidence
   `tun_up`/`vpn_connected`, không raise như `require_android_vpn`. File mapping:
   `D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx` (header `máy, device id, proxy`).
6. **Launch (nếu được authorize)**: lệnh `am start -W -n <pkg>/<activity>`.
   ⚠️ rc=0 KHÔNG phải proof — parse stdout/stderr `Error type N`. Sau đó poll
   foreground qua `dumpsys activity activities` (KHÔNG uiautomator dump — hang trên
   Samsung):
   - `mResumedActivity:\s*ActivityRecord\{[^}]*\s+([^/\s]+)/([^/\s]+)`
   - `mCurrentFocus=Window\{[^}]*\s+([^/\s]+)/([^/\s}]+)` — chú ý `}` cuối dòng,
     regex phải loại `}` khỏi class char (bug đã gặp: parse ra `MainActivity}`).
   - Timeout ~45s; không lên foreground → blocker `TIKTOK_NOT_FOREGROUND`, không
     recovery, không relaunch.
7. **Capture read-only khi còn giữ lock**: chạy tool repo
   `python tools/dump_selectors.py --serial <S> --out-dir runs/probes --adb-path ...`
   (screencap + uiautomator dump + summary JSON sanitized). Artifact name:
   `capture_<tsUTC>_<serialhash12>_<label>.{png,xml,json}` — không chứa serial thô.
   Nếu `uiautomator dump` trả rc=137 (atx wedged) → ghi blocker, KHÔNG pkill trong
   scope read-only.
8. **Release lock trong `finally`**: `lease.release_with_audit(reason=...)` →
   `released_paths` là list[str] (format `str(p)`, không `.name`). Sau release
   VERIFY lock dir: không còn `machine_<N>`/`serial_<S>` lock của target.
9. **Artifact tổng hợp**: manifest/evidence JSON sanitized dưới `runs/probes/`
   (chỉ serial hash + serial_tag 8 hex; không serial thô, không credential, không
   nội dung proxy).

## Blocker đã gặp live (2026-08-12, máy 1)

- `am start -W -n com.ss.android.ugc.trill/.main.MainActivity` → stdout:
  `Error type 3 / Activity class {com.ss.android.ugc.trill/com.ss.android.ugc.trill.main.MainActivity} does not exist.`
  rc vẫn = 0. Component không launch được trên bản TikTok máy này → không có
  foreground; theo scope cấm relaunch nên không thử `monkey`/activity khác.
  Bước kế (cần user duyệt): `cmd package resolve-activity --brief com.ss.android.ugc.trill`
  để lấy launchable activity thật, hoặc `monkey -p com.ss.android.ugc.trill 1`.
- `uiautomator dump` rc=137 (atx wedged) — screencap/dump của probe không có;
  ghi blocker, không recovery.
- Máy rớt khỏi `adb devices` ngay sau probe (offline/disconnect) — evidence bổ
  sung, không recovery.

## Probe tool tái dùng (đã tạo trong tiktok-follow/tools, chưa commit)

`probe_mode2_{launch,helpers,capture,wait,main}.py` — orchestration trên:
lock/preflight/launch-once/wait-foreground/capture/release. Chạy:
`env -u PYTHONPATH 'D:/Taadaa/python-envs/automation/Scripts/python.exe' tools/probe_mode2_main.py`
(lưu ý pitfall PYTHONPATH bleed — phải `env -u PYTHONPATH` với venv automation).
