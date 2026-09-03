# Device-lock removal (user decision 2026-08-15) — evidence + scope

## User decision (verbatim intent, repeated 3×)

- "xoá luôn hết tất cả cơ chế lock khỏi repo"
- "đã bảo là... bỏ hết cơ chế lock chỉ lock khi t ra lệnh lock khỏi repo"
- "T ra lệnh lock máy nào ms đc lock còn k xoá hết auto lock"
- "Kể cả preflight t chạy script loz nào cx gặp lock r mất 30ph-1h cho nó dọn cứt xong ý"
- "Vấn đề lock cũ nó cứ gây lỗi suốt mà bữa t cho quét log rồi thì lỗi lock hơn 7000 lần trong 1 tuần thì phải"
- "Xoá hết lock" (clarify: giữ FAILED_LOCKED policy? → "Xoá hết lock")

Kết luận: lock device CHỈ khi user ra lệnh; KHÔNG auto acquire/release/check/
FAILED_LOCKED. **GIỮ NGUYÊN:** journal/file lock (msvcrt/thread — bảo vệ đọc
ghi dữ liệu) và **lock gan-proxy** ("riêng lock của ganproxy là k đc xoá").

## Bằng chứng log thật (main repo, KHÔNG worktree)

`/d/Taadaa/tiktok-luot nuoi acc/python_runner/runs/`:
- `scheduler.jsonl` (24KB):
  - 2026-08-03: `ImportError: cannot import name 'FULL_SCOPE_TAKEOVER' from 'automation_core.device_lock'` → failed
  - 2026-08-04/07/08/10: `"multi-machine-feed-session skipped locked machine(s)"` → manual-needed exit 2 (hàng loạt máy skip)
  - 2026-08-05: `DEVICE_LOCK_STATUS_OWNERSHIP_MISMATCH` → failed
  - 2026-08-14/15 (4 shifts row 6,2,3,1): `ImportError: cannot import name 'DeviceLockNeedsUserDecision' from 'automation_core.device_lock'` → failed 3.9s exit 1 — **MỌI batch fail từ 14/08**
- `device-lock-release-audit.jsonl` (52 dòng): `DEVICE_LOCK_RELEASED` manual-release — chính là script release-device-lock.py (dọn lock tay)
- `schedule-recovery-ledger.jsonl` (2.6MB): 950+ "lock" refs
- `~/.codex/device-locks/`: 90 mục (backup_* + evidence_* + lock thật)
  - `machine_65.lock.json` + `serial_ce12160c4a45432204.lock.json`: PID 24568, host DESKTOP-3PFPGQC, project **gan-proxy/scripts/vi_changer_runner.py** → CẤM đụng
  - `machine_99999.lock.json`: offline-test PID 42260 (test sót)
  - `quarantine/`: đầy lock cũ

## Root cause chuỗi fail 14-15/08

`automation_core.device_lock` (installed) KHÔNG export `DeviceLockNeedsUserDecision`
(verify: `dir()` thấy FULL_SCOPE_TAKEOVER, SAME_PROJECT_RECOVERY,
acquire_device_lock, DeviceLockUnavailable, device_lock_paths, DeviceLockLease —
KHÔNG thấy DeviceLockNeedsUserDecision). Consumer vẫn import ở 4 chỗ:
- `python_runner/core/device_lock.py:7,17`
- `python_runner/flows/multi_machine_feed_session.py:25,1182`
- `python_runner/run_tiktok.py:20,863`

→ ImportError chết ngay khi import module → batch fail 3.9s.

**Lưu ý worktree vs main:** worktree `phase9-authority-910a8add` ĐÃ sạch symbol
này (code Phase 9 mới) nhưng vẫn còn auto-lock (FULL_SCOPE_TAKEOVER,
acquire_device_lock...); main repo vẫn còn cả hai. Batch thật chạy MAIN repo.

## Cách xoá (TDD, tuần tự — commit 1 trước)

Commit 1 (đường live 9C.2): `live_entrypoint.py` + `pilot.py`
- Bỏ `_production_lock_reader`, `_LOCK_ACTIVE_BLOCKED`, `_device_lock_paths` import
- `_validate_permit`: bỏ `lock_reader` param + F3 block (dòng "F3: read the actual shared device lock")
- `run_once`: bỏ `lock_reader` param, `FAILED_LOCKED` → `FAILED` (giữ fail-closed, không giữ lock)
- `pilot.py`: không dính (chỉ 1 dòng comment)

Commit 2 (flows/core/job_spec): `core/device_lock.py`,
`flows/multi_machine_feed_session.py` (imports L11/22/25, `_device_lock_root`,
`_observed_lock_aliases`, `_target_lock_aliases`, `_lock_release_proof`,
acquire/release, `_LOCK_HANDOFF_SCHEMA`, `recovery_lock_handoff.json`),
`flows/multi_machine_smoke.py`, `flows/feed_swipe_smoke.py` (FAILED_LOCKED),
`run_tiktok.py` (L20 import sai + acquire L851), `job_spec.py`
(stale_classification FAILED_LOCKED → FAILED), `scripts/release-device-lock.py`
(có thể giữ làm tool tay). Cập nhật 15+ test files (bỏ `lock_reader=` kwarg,
`FAILED_LOCKED`→`FAILED`, xoá test lock_reader).

## Cảnh báo khi làm

- Đừng hỏi lại scope nhiều lần — user đã bực ("khoan hỏi ngoài lề", "Làm. Đi").
- User muốn kiểm tra log TRƯỚC khi cắt ("Trc tiên kiểm tra lịch sử log đi. Xem
  con số khổng lồ t đưa ra có đúng k") — luôn proof log trước khi sửa.
- Đừng quét toàn ổ D (timeout) — quét đúng `runs/` + `~/.codex/device-locks/`.
- `find /d/OneDrive` timeout (OneDrive to) — đừng quét.
- `taikhoan_run_safe.xlsx` cột `May`=số máy; row 2 của máy 5 = slot 2 (không phải
  excel row 2). Serial máy 5 = `9885e64b4a434a3037`, account slot 2 = `stevemgjqec`.

## ADDENDUM 2026-08-16 — root cause + fix đã chứng minh (version skew 3 env)

ImportError `DeviceLockNeedsUserDecision` liên tục từ 14/08 KHÔNG phải do thiếu
symbol trong core source — class CÓ trong **automation-core 0.4.45** (thêm ở commit
lock-gate `d0bab14`), nhưng 3 Python env trên host đang giữ 3 version khác nhau:

- hermes-agent venv = **0.4.43** (KHÔNG có class)
- Python312 global (`C:\Users\Kibe\AppData\Local\Programs\Python\Python312`) = **0.4.44** (KHÔNG có)
- `D:\Taadaa\python-envs\automation` = **0.4.45** (CÓ — đã verify `hasattr(d,'DeviceLockNeedsUserDecision')`)
- `run-feed-session.ps1` default `$Python = "python"` → bare python = Python312/0.4.44 → fail. Task At-logon còn spawn 2 process scheduler song song qua 2 env (automation + Python312).

**Fix**: đồng bộ cả 3 env về 0.4.45, cài bằng Windows path KHÔNG phải MSYS `/d/...`:
```
python -m pip install --force-reinstall "file:///D:/Taadaa/automation-core-user-lock-gate-wt/dist/automation_core-0.4.45-py3-none-any.whl"
```
Verify bằng import smoke từ CHÍNH env: `python -c "import automation_core.device_lock as d; print(hasattr(d,'DeviceLockNeedsUserDecision'))"` — pip show version KHÔNG đủ (dist-info có thể lag).

**Lesson chẩn đoán chung**: traceback hiển thị path của env mà process resolve
(vd hermes venv) — nhìn path KHÔNG tự kết luận "PYTHONPATH leak"; hỏi đúng câu
"symbol này có trong version nào" → `pip show automation-core` + `dir()` từng env
cùng lúc. Lịch sử 08-03 cũng cùng pattern (`FULL_SCOPE_TAKEOVER` thiếu ở bản cũ).
