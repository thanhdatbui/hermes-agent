# Tiktok-video Upload Batch (đăng video all máy, mỗi máy 1 video)

Runbook rút gọn từ session 2026-08-07: chạy đăng video toàn bộ máy trong workbook TikN qua
`Tiktok-video` (KHÁC repo `Tiktok_Reg` — đây là pipeline upload, không phải registration).

## Pipeline & paths
- Repo: `D:\Taadaa\Tiktok-video`. Scripts: `scripts/tiktok_workflow/` (machine_inventory, run_post,
  state_machine, post_verifier, report, media_manager).
- Launcher: `run_tiktok_upload_batch.ps1` — params:
  `-Tik N` (1..99), `-MaxParallel`, `-Confirmation RUN` (live; bắt buộc, so khớp chữ hoa "RUN"),
  `-PreflightOnly`, `-ProfileSmoke`, `-RecoveryMode`, `-ForceAvatarMachineList`,
  `-AssignmentManifest`/`-WorkerId` (giới hạn scope), `-LockRoot` (mặc định `$env:CODEX_DEVICE_LOCK_DIR`),
  `-PythonPath` (mặc định venv-core024).
- Workbook: `D:\OneDrive\Tiktok\TikN.xlsx`, sheet `TaiKhoan`. Cột: Máy | device ID | ID (TikTok) |
  Folder Video | video gốc | Keyword Video | Hashtag Pool | Video Đã Đăng | Kiểm Tra Dữ Liệu.
  Nguồn tài khoản: `D:\OneDrive\Tiktok_Reg\taikhoan_dat_v2_updated.xlsx`.
- Config: `D:\CodexRuntime\tiktok-video\config-machine-62.yaml`; runtime:
  `D:\CodexRuntime\tiktok-video\venv-core024\Scripts\python.exe` (automation-core 0.4.40).
  Launcher hardcode `$defaultAutomationCoreVersion = "0.4.40"` và **fail cứng nếu version lệch**.
- Media: `D:\TIKTOK-videonuoinick\<folder>` (mỗi máy 1 folder đã render; "mỗi máy 1 video" =
  workflow tự chọn video kế theo cột Video Đã Đăng).

## Quy trình chuẩn
1. **Preflight read-only** (KHÔNG đăng gì) — xem trước máy eligible vs bị skip:
   ```bash
   cd /d/Taadaa/Tiktok-video && PYTHONPATH= /d/CodexRuntime/tiktok-video/venv-core024/Scripts/python.exe \
     -m tiktok_workflow.machine_inventory --workbook "D:/OneDrive/Tiktok/Tik1.xlsx" \
     --max-workers 30 --min-stagger-ms 2000 --max-stagger-ms 8000
   ```
   JSON: `eligible` (máy sẽ chạy), `skipped` (mỗi entry machine/status/reason:
   `SKIPPED_LOCKED` = device lock present, `SKIPPED_INVALID` = missing/invalid serial,
   `SKIPPED_DISABLED`, `SKIPPED_ASSIGNMENT` = outside worker manifest), `machine_launch`
   (random order + bounded stagger 2000-8000ms, max_workers = min(max_workers, len(entries)),
   seed ngẫu nhiên mỗi run).
2. KHÔNG truyền assignment manifest → chạy **TOÀN BỘ** máy có serial hợp lệ trong workbook,
   lock tự loại (đúng yêu cầu "all máy trừ máy lock"). Có manifest + worker-id → chỉ máy trong
   manifest (`automation_core.assignments.AssignmentManifest`, owner_id phải khớp, manifest MỚI mỗi retry).
3. Live: `powershell -ExecutionPolicy Bypass -File run_tiktok_upload_batch.ps1 -Tik 1 -MaxParallel 8 -Confirmation RUN`.
4. Kết quả: `D:\CodexRuntime\tiktok-video\batch-runs\batch_tik1_<list>_<ts>\summary.csv` +
   `machine-launch.json` (evidence redacted: seed/order/delay). Per-machine stdout/stderr logs.

## Pitfalls (đều gặp thật 2026-08-07)

### P1: PYTHONPATH của Hermes che automation-core của venv → version mismatch
- Triệu chứng: launcher throw `automation-core version mismatch: expected=0.4.40; actual=0.4.32`
  dù venv-core024 CÓ `automation_core-0.4.40.dist-info` đúng.
- Nguyên nhân: terminal Hermes export
  `PYTHONPATH=C:\Users\Kibe\AppData\Local\hermes\hermes-agent;...\venv\Lib\site-packages` →
  `import automation_core` resolve vào hermes venv (0.4.32) TRƯỚC venv project.
- Debug nhanh:
  `python -c "import automation_core; print(automation_core.__file__); import importlib.metadata as m; print(m.version('automation-core'))"`
  — nếu `__file__` trỏ hermes venv thì đúng bệnh.
- Fix: `PYTHONPATH=` (rỗng) trước mọi lệnh python/powershell trong session.

### P2: Eligible ≠ postable — máy MISSING_ID fail-closed
- `machine_inventory` chỉ check serial (cột device ID), KHÔNG check cột ID TikTok.
- Máy 75/77/78/79/80 (Tik1) có serial hợp lệ → vào `eligible`, nhưng ID trống (Kiểm Tra = MISSING_ID)
  → workflow fail: `Missing required fields: ID TikTok` → exit 1, KHÔNG đăng gì (fail-closed đúng).
- Trước khi chạy live: đối chiếu cột ID của các máy eligible; trống → không kỳ vọng success,
  cần điền ID từ `taikhoan_dat_v2_updated.xlsx` trước.

### P3: Lock có thể xuất hiện giữa preflight và launch
- Máy 4/25/66 eligible lúc preflight nhưng bị scheduler khác (feed/login/reg) giữ lock ngay sau đó
  → thành SKIPPED_LOCKED trong summary. **Summary cuối là nguồn sự thật, không phải preflight.**

### P4: Launcher chạy qua bash background + `| tail` trông như treo
- Sau khi summary.csv đã ghi, process có thể vẫn "running" do pipe chưa EOF. Đừng chờ exit —
  đọc summary.csv trực tiếp (python csv, encoding utf-8-sig). Kill process treo an toàn:
  job con đã ghi xong file.

### P5: Ý nghĩa ExitCode trong summary
- `0` = THÀNH CÔNG — bắt buộc `report.status == "SUCCESS"` AND `post_verified == true`;
  exit 0 mà thiếu report/verifier proof → chuyển MANUAL_REVIEW (effective 2).
- `2` = worker exit 0 nhưng thiếu proof → MANUAL_REVIEW.
- `3` = SKIPPED_LOCKED / SKIPPED_ASSIGNMENT / SKIPPED_INVALID — không phải success, không FINAL_BLOCKED.
- `1` = LỖI → đọc `machine-<n>.err.log`.
- Report `LOGIN_RECOVERY_REQUIRED` = classified manual checkpoint; launcher KHÔNG tự recovery/requeue
  (cần RecoveryMode owner riêng, target-specific).

## Xác nhận thành công thật
- Log `Report saved: <path>\report.json` → `status == "SUCCESS"` + `post_verified == true`.
- "Post verification SUCCESS generic marker" = bài ĐÃ đăng (ACCEPTED) → hậu kiểm tay + cập nhật
  ledger, KHÔNG retry.
- Lock policy: success → release; crash/timeout → handoff (giữ lock cho recovery).

## P6: Dọn lock stale (pid chết) — pattern đã dùng 2026-08-07, user duyệt cho farm này

Triệu chứng: preflight báo 70+ máy `SKIPPED_LOCKED` dù không có tiến trình nào thật sự chạy.

- **Mỗi máy có HAI lock file**: `machine_<n>.lock.json` + `serial_<serial>.lock.json`.
  `machine_inventory._filter_locks` gọi `device_lock_paths(machine, serial, lock_root)` → check
  CẢ 2 loại. **Chỉ archive machine_*.lock.json KHÔNG đủ** — phải archive serial_* luôn.
- Kiểm tra pid sống tin cậy: `tasklist` silent-fail trong git-bash (trả rỗng dù pid còn sống).
  Dùng 1 lần `wmic process get ProcessId` snapshot toàn bộ → set membership; hoặc
  `wmic process where "ProcessId=N" get ProcessId` (đáng tin).
- Cách dọn: **MOVE (không delete)** vào `D:\CodexRuntime\tiktok-video\stale-lock-archive\<ts>_m<n>/`
  (thư mục này đã có precedent từ 2026-07-30). Giữ nguyên các máy: pid ALIVE + user chỉ định.
- Lock file có `takeover_from` + `takeover_authorization.scope=FULL_SCOPE_TAKEOVER` = lock đã bị
  handler khác ghi đè (vd Tiktok_Reg recovery `--full-scope-takeover`) — pid trong lock có thể
  đổi nhiều lần (running→blocked). Chỉ tin pid hiện tại trong file, không tin lịch sử.
- Sau khi archive: chạy lại preflight để xác nhận eligible đúng như kỳ vọng trước khi live.

## P7: Phân loại lỗi batch — đọc report.json gom theo reason

Sau batch live, máy lỗi (exit 1) có report trong `D:\CodexRuntime\tiktok-video\runs\run_*/report.json`.
Gom nhanh theo `status + reason` (lọc timestamp đúng khung giờ batch) để biết lỗi nào phổ biến:

```python
import json, glob
from collections import Counter
reasons = Counter()
for rp in glob.glob(r'D:\CodexRuntime\tiktok-video\runs\run_*\report.json'):
    d = json.load(open(rp, encoding='utf-8'))
    if not str(d.get('timestamp','')).startswith('2026-08-07T13:4'): continue  # khung giờ
    reasons[d.get('status','?') + ' | ' + str(d.get('reason',''))[:80]] += 1
for k,v in reasons.most_common(15): print(v, k)
```

Failure signatures gặp thật (run 2026-08-07, ~31 máy lỗi UI):
- `POST_CONTROL_OCCLUDED_RECOVERY_FAILED` — composer bị che; Back không recapture được final
  composer có guard caption + Post → MANUAL_REVIEW (phổ biến nhất).
- `[UI_DUMP_FAILED] uiautomator_idle_state_error` trong DISMISS_POPUPS — không đọc được UI.
- `[OPEN_TIKTOK_FAILED]` — TikTok không vào feed sau 1 lần force-stop + launch.
- `[DEVICE_STARTUP_FAILED] ui_dump_error: non_xml_ui_dump`.
- Máy MISSING_ID (73/75/77/78/79/80 Tik1) fail-closed ngay không có report — chỉ err.log.

Batch 78 máy (37 success / 6 lock / 37 lỗi): tỷ lệ ~50% success lượt đầu là bình thường với farm
này — lỗi UI đa số transient, retry 1 lần có thể qua; máy MISSING_ID phải điền ID trước.

