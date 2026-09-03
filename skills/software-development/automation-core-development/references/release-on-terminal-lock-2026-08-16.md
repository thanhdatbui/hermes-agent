# Release-On-Terminal Device Lock — audit loop + design (2026-08-16)

User: "lúc chạy thì lock lại, chạy xong dù có success hay fail block gì cũng gỡ lock ra hết — tránh tình trạng cứ làm gì cũng ăn lock của cơ chế cũ, nhưng bảo vệ đc 1 máy chỉ đc chạy 1 script 1 lúc."

## Root cause lock-death (verified từ code)

| Nguồn | Cơ chế | Trạng thái 16/08 |
|---|---|---|
| `scheduler/base.py:298` `DeviceLock(...)` default `user_authorized=True` | Tạo file lock thật + `wait_for_proxy_ready` 180s; fail → `set_status("failed_locked"/"handoff")` GIỮ VĨNH VIỄN → `_device_lock_available()` False mọi run sau → `skipped-device-locked` | **NGUỒN DUY NHẤT còn lại** |
| `recovery_runner` | Nhận lock từ `target.acquire_lock()` (consumer cung cấp) — không tự tạo | Không phải nguồn |
| `recovery.py` FAILED_LOCKED | Queue-state + `_failed_locked_hold` retention | OUT OF SCOPE (giữ) |
| Consumer repos (Tiktok_Reg, feed, f2a, follow) | Đã migrate `user_authorized=False` → no-op lease, không tạo lock | Không phải nguồn |

## Luồng audit (4 vòng plan, Claude CLI opus-5)

1. **V1 (default True) → REJECT 2 CRIT**: C1 default True = silent breaking change mọi caller; C2 FAILED_LOCKED release = mất hold-signal chống re-queue. + 3 MAJOR + 2 MINOR.
2. **V2 (default False + state.json hold-signal + recovery out-of-scope) → MINOR_FIXES**: F1 (giả định `serve()` gate failed-locked chưa verify — ĐÚNG, code KHÔNG có gate), F2 (crash path cũng release chưa document), F3 (locks.py wrapper `__exit__` phải unlink file qua canonical release, không FileLease.update), F4/F5 (test phải assert file absence).
3. **V3 (verify F1 bằng code thật: serve() chỉ gate awaiting-verified-terminal-result → retry daily = INTENTIONAL theo user; crash release = intentional; locks.py unlink; tests file-absence) → MINOR_FIXES**: chỉ còn A (default phải ghi rõ False — plan v3 ĐÃ ghi rõ, auditor không đọc được file nên sót), B (CLI visibility LOW), C (INFO retry daily vô hạn).
4. **V4 = sửa A/B/C → APPROVED path** (chưa chạy hết do session cắt — plan đã hoàn chỉnh).

## Bài học audit-loop

- **AG hallucinate toàn bộ source ảo** (bịa API `device_name`/`lock_file`/`_try_acquire`/`_StaleLockReaped` không tồn tại; line numbers khác hẳn) → verdict vô dụng, bỏ. Claude CLI opus-5 "File access denied" nhưng vẫn cho verdict tốt vì prompt self-contained.
- **Prompt audit self-contained** (paste REAL source + line numbers + pitfalls + plan + questions; cấm đọc file ngoài) = method hoạt động. Recipe: `hermes-orchestration-dispatcher` → `references/self-contained-audit-prompt-recipe.md`.
- **Auditor giả định phải verify bằng code thật**: giả định "state.json gate failed-locked" SAI — `serve()` chỉ gate `awaiting-verified-terminal-result`. Resolution theo USER INTENT (retry daily intentional), KHÔNG thêm gate ngoài yêu cầu.
- Findings giảm dần REJECT→MINOR_FIXES→MINOR_FIXES = đúng quỹ đạo; chỉ audit Δ mỗi vòng (v2 findings → v3 resolutions + verified facts).

## Design cuối (v4)

```python
# device_lock.py
@dataclass
class DeviceLockLease:
    lock_paths: list[Path]; host: str; pid: int; lock_id: str
    release_on_terminal: bool = False   # append: bool = False (opt-in!)
    _released: bool = field(default=False, init=False, repr=False)

    def finish(self, *, succeeded, failure_status="handoff"):
        if succeeded or self.release_on_terminal:
            self.release()
        else:
            self.set_status(failure_status)

    def __exit__(self, exc_type, exc, tb):
        if self._released: return
        if self.release_on_terminal:
            self.release(); return
        # legacy: set_status("handoff") + note
```

- `acquire_device_lock(...)`: thêm `release_on_terminal: bool = False` SAU `live_vpn_verifier` (LAST kwarg); thread vào cả 2 lease constructions.
- `DeviceLock` compat: thêm kwarg LAST (sau `user_authorized`); update `test_device_lock_preserves_legacy_positional_parameter_order` name list.
- `_UnlockedDeviceLockLease`: override `finish`/`__exit__` no-op hay đã có — verify `__exit__` hiện kế thừa parent (nguy hiểm dưới release_on_terminal=True vì parent release chạy trên lock_paths=[]) → thêm override explicit.
- `locks.py`: `acquire_device_lock` + `DeviceLockLease` accept `release_on_terminal`; delegation forward; wrapper `__exit__` khi True → canonical `release()` (unlink), KHÔNG `FileLease.update(status=...)`.
- `scheduler/base.py:298`: `DeviceLock(..., release_on_terminal=True)`; FAILED_LOCKED branch giữ `state["status"]="failed-locked"` (report) + comment "lock released on every outcome; retry next daily slot intentional; operator remove from roster if manual intervention needed".
- `_device_lock_available()` KHÔNG đổi.

## Test map

`tests/test_release_on_terminal.py` (CRLF):
1. default-retains-failure (finish(succeeded=False) → file còn + status handoff)
2. opt-in-finish-failure-releases (file ABSENT)
3. opt-in-context-exception-releases (file ABSENT)
4. default-context-exception-retains (file còn)
5. unlocked-noop-never-writes (user_authorized=False + release_on_terminal=True → không file)
6. DeviceLock-compat-opt-in (file ABSENT)
7. legacy-locks-wrapper-opt-in-releases (file ABSENT)
8. legacy-locks-wrapper-context-exit-releases (file ABSENT)

Full suite baseline: 572 pass + 1 pre-existing `test_startup` fail. `PYTHONPATH=src` bắt buộc.

Plan file: `automation-core/.hermes/plans/2026-08-16_230649-release-always-device-lock.md`.