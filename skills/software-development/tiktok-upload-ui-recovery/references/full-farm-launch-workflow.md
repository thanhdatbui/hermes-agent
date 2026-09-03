# Full-farm launch: tất cả máy trừ N (2026-08-08, Tik1)

Quy trình chạy batch đăng video **toàn bộ máy trong workbook trừ một máy cụ thể**
(user: "chạy đăng video all máy trừ máy 34") — khác retry-batch (chỉ máy lỗi):
ở đây cần **dọn lock stale hàng loạt trước** vì nếu không inventory sẽ
SKIPPED_LOCKED gần hết farm.

## 1. Preflight inventory (read-only, KHÔNG mở app)

```bash
cd /d/Taadaa/Tiktok-video
PYTHONPATH='D:\Taadaa\Tiktok-video\scripts' /d/CodexRuntime/tiktok-video/venv-core024/Scripts/python.exe -c "
from tiktok_workflow.machine_inventory import build_inventory
inv = build_inventory(r'D:\OneDrive\Tiktok\Tik1.xlsx')
print('ELIGIBLE:', sorted(inv['eligible']))
print('SKIPPED:', [(s['machine'], s['status']) for s in inv['skipped']])
"
```
- Kết quả `SKIPPED_LOCKED` cho 60+ máy = lock files tồn tại (có thể STALE).
- ⚠️ PYTHONPATH phải dùng **Windows path** (`D:\...`), MSYS path (`/d/...`)
  không được Python Windows nhận.

## 2. Phân loại lock: stale (pid chết) vs thật (process sống)

- Đọc từng `~/.codex/device-locks/machine_*.lock.json`: field `project`, `pid`,
  `status`, `owner_active`, `command`.
- **Feed scheduler `tiktok-luot nuoi acc`**: 1 pid giữ 30+ máy cùng lúc
  (`run_tiktok.py --mode multi-machine-feed-session`). PID chết → lock stale.
- **Watcher gan-proxy** (`gan_proxy_fleet.py watch`): giữ máy theo chu kỳ poll.
- **Máy cần trừ** (VD 34): `Tiktok_Reg` đang giữ `status=blocked` cho recovery
  → **giữ nguyên lock, không đụng**, chỉ loại khỏi manifest.
- Verify pid sống: `tasklist //FI "PID eq N"` (trả dòng chứa PID = sống).
- ⚠️ Có 2 file/máy: `machine_<m>.lock.json` + `serial_<serial>.lock.json` —
  phải xử lý cả 2.

## 3. Dọn lock stale có backup + evidence (script `scripts/lock_cleanup_stale.py`)

Pattern đã verify 2026-08-08 (118 lock removed, 2 kept = máy 34):
- **Backup TOÀN BỘ** lock files vào `backup_takeover_<ts>/` trước khi xóa.
- Chỉ xóa lock có pid **chết** (fail-closed: không verify được pid → giữ).
- **KEEP_MACHINE set** = máy user yêu cầu trừ (giữ nguyên lock).
- Ghi `evidence_takeover_<ts>.json` liệt kê removed/kept + lý do + `pid_alive`.
- Chạy lại inventory (bước 1) → giờ phải `ELIGIBLE = 1..80 trừ N`, chỉ còn
  máy N trong `SKIPPED_LOCKED`.

Script nằm tại `D:\Taadaa\Tiktok-video\scripts\lock_cleanup_stale.py` (tái dùng,
chỉnh `KEEP_MACHINE` theo user request).

## 4. Assignment manifest — 79 máy trừ 34

`D:\CodexRuntime\tiktok-video\assignments\tik1-all-except-34-20260808.json`:
```json
{
  "schema_version": 1,
  "assignment_id": "tik1-all-except-34-20260808",
  "owner_id": "hermes-tik1-all-except-34",
  "resources": ["machine:1", ..., "machine:33", "machine:35", ..., "machine:80"],
  "reviewed_at": "2026-08-08T11:30:00+07:00"
}
```
Verify trước khi launch:
```python
from automation_core.assignments import AssignmentManifest
m = AssignmentManifest.load(r'...json')
m.assert_owner('hermes-tik1-all-except-34')
res = sorted(int(r.split(':')[1]) for r in m.resources if r.startswith('machine:'))
assert res == [n for n in range(1, 81) if n != 34] and len(res) == 79
```

## 5. Launch batch (background + notify_on_complete)

```bash
unset PYTHONPATH
cd /d/Taadaa/Tiktok-video && powershell -NoProfile -ExecutionPolicy Bypass \
  -File run_tiktok_upload_batch.ps1 -Tik 1 -MaxParallel 10 \
  -AssignmentManifest 'D:\CodexRuntime\tiktok-video\assignments\tik1-all-except-34-20260808.json' \
  -WorkerId 'hermes-tik1-all-except-34' -Confirmation RUN
```
- `unset PYTHONPATH` bắt buộc — xem SKILL.md §4 (pitfall MSYS export → version mismatch).
- Chạy `terminal(background=true, notify_on_complete=true)` — 79 máy mất nhiều giờ.

## 6. Trong lúc batch chạy — lock MỚI xuất hiện là BÌNH THƯỜNG

Sau launch, `~/.codex/device-locks/` có thêm `machine_*.lock.json` với
`project=tiktok-upload`, `owner_active=true` = **runner của batch vừa acquire**.
Đừng nhầm là lock cũ quay lại; xác minh bằng `project == "tiktok-upload"` +
pid sống. Máy vào `handoff` (owner_active=false) = runner fail giữ cho recovery
(đúng thiết kế, KHÔNG tự retry).

## 7. Ad-hoc verify các artifact (manifest + cleanup) — tempfile script

Không có canonical test cho manifest/cleanup; dùng script tạm
`hermes-verify-*.py` trong `%TEMP%` (tempfile.mkstemp prefix `hermes-verify-`):
- `py_compile` cleanup script.
- Evidence JSON: removed>0, all `pid_alive=False`, máy trừ nằm trong `kept`.
- Manifest: owner ok, count đúng, máy trừ vắng mặt.
- Lock hiện tại: ngoài máy trừ, mọi lock còn lại thuộc `project=tiktok-upload`.
Chạy bằng venv-core024 python, xóa script sau khi xong, báo rõ là
"ad-hoc verification (không phải suite green)".
