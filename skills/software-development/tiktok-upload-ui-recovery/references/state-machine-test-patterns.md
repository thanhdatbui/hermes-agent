# State Machine Regression Test Patterns (Tiktok-video consumer)

Các template test đã verify live (2026-08-07, batch retry 13-16). Copy-modify khi
viết regression test cho fix trong `scripts/tiktok_workflow/state_machine.py`.

## 1. Test soft-reboot recovery trigger trong DISMISS_POPUPS

Bảo vệ: nhánh `UI_DUMP_FAILED` của DISMISS_POPUPS gọi `_maybe_soft_reboot_recovery()`
trước `return False` (fix idle_state_error 2026-08-07).

```python
def test_dismiss_popups_ui_dump_failed_triggers_soft_reboot(self, monkeypatch, tmp_path):
    """DISMISS_POPUPS UI_DUMP_FAILED (idle_state_error) must trigger the
    bounded soft-reboot recovery instead of MANUAL_REVIEW immediately."""
    from pathlib import Path
    from tiktok_workflow.state_machine import StateContext, StateMachine, WorkflowError, WorkflowState

    class Transport:
        def screenshot(self, path):
            Path(path).write_bytes(b"artifact")
            return True

    context = StateContext(
        config={
            "allow_device_reboot_recovery": True,
            "tiktok_package": "com.example",
            "soft_reboot_recovery_max_total": 1,
        },
        adb_client=object(),
        adapter=object(),
        device_transport=Transport(),
        reporter=type("Reporter", (), {"run_dir": tmp_path})(),
        dry_run=False,
    )
    machine = StateMachine()
    machine.context = context
    # PHẢI monkeypatch đủ 5 thứ — thiếu cái nào cũng return False:
    monkeypatch.setattr(machine, "_save_checkpoint", lambda **_kwargs: None)
    monkeypatch.setattr(machine, "_soft_reboot_recovery", lambda *_args: True)
    monkeypatch.setattr(machine, "_package_is_foreground", lambda *_args: True)  # True, không phải False!
    monkeypatch.setattr(machine, "_capture_soft_reboot_artifact", lambda _phase: tmp_path / "artifact.png")
    monkeypatch.setattr(machine, "_reserve_proxy_recovery_handoff", lambda _sig: (None, None))

    machine.current_state = WorkflowState.DISMISS_POPUPS
    error = WorkflowError(
        WorkflowState.DISMISS_POPUPS,
        "DISMISS_POPUPS không đọc được UI: uiautomator_idle_state_error",
        "UI_DUMP_FAILED",  # error_code THUẦN, không phải chuỗi message dài
    )
    assert machine._maybe_soft_reboot_recovery(error=error)
    assert context.soft_reboot_recovery_total == 1
    context.recovery_resume_state = None
    # Cùng signature không reboot lần 2 (bounded).
    assert not machine._maybe_soft_reboot_recovery(error=error)
    assert context.soft_reboot_recovery_total == 1
```

**Pitfall chi tiết từng monkeypatch** (đã debug qua 3 lần fail):
- Thiếu `_capture_soft_reboot_artifact` patch + dùng Transport thật với `run_dir`
  không tồn tại → `Path.write_bytes` FileNotFoundError → artifact None → `return False`.
  Luôn patch trả Path sẵn có.
- `_package_is_foreground=False` → sau reboot `foreground is not True` →
  RECOVERY_FAILED → `return False`. Phải True.
- `_reserve_proxy_recovery_handoff` không patch → chạy thật cần `device_lease`
  + `read_readiness(serial)`; serial rỗng trong test có thể return (None, None)
  nhưng patch cho chắc.
- WorkflowError tham số: `(state, message, error_code)` — error_code là tham số 3.

## 2. Test media fingerprint stale release

Bảo vệ: `media_fingerprint.py::reserve()` release reservation cũ > stale_after_seconds
nhưng KHÔNG bao giờ release verified_success.

```python
def test_fingerprint_stale_reservation_is_released_and_never_verified(self, tmp_path):
    from tiktok_workflow.media_fingerprint import (
        MediaFingerprintLedger,
        MediaFingerprintDuplicateError,
    )
    source = tmp_path / "video.mp4"
    source.write_bytes(b"stale exact video bytes")
    ledger = MediaFingerprintLedger(tmp_path / "runtime")

    # Worker 1 reserve rồi crash (run không finalize).
    ledger.reserve(machine="44", target_account="account-44", video_number=5,
                   source_path=source, run_id="dead-run")
    # Worker 2: stale_after_seconds=0 force path stale ngay (không cần sleep).
    reservation = ledger.reserve(machine="44", target_account="account-44",
                                 video_number=5, source_path=source,
                                 run_id="retry-run", stale_after_seconds=0)
    assert reservation.run_id == "retry-run"

    # Sau finalize (post verified) → hash là duplicate vĩnh viễn.
    ledger.finalize(reservation)
    try:
        ledger.reserve(machine="44", target_account="account-44", video_number=5,
                       source_path=source, run_id="third-run", stale_after_seconds=0)
        raise AssertionError("verified_success must never be released")
    except MediaFingerprintDuplicateError:
        pass

def test_fingerprint_fresh_reservation_is_not_released(self, tmp_path):
    """Reservation trẻ hơn stale_after_seconds phải stay pending (worker có thể còn sống)."""
    from tiktok_workflow.media_fingerprint import (
        MediaFingerprintLedger, MediaFingerprintPendingError,
    )
    source = tmp_path / "video.mp4"
    source.write_bytes(b"fresh exact video bytes")
    ledger = MediaFingerprintLedger(tmp_path / "runtime")

    ledger.reserve(machine="48", target_account="account-48", video_number=5,
                   source_path=source, run_id="live-run")
    try:
        ledger.reserve(machine="48", target_account="account-48", video_number=5,
                       source_path=source, run_id="second-run")  # default 1800s
        raise AssertionError("fresh reservation must stay pending")
    except MediaFingerprintPendingError:
        pass
```

## 3. Chạy test

```bash
# Consumer convention: PYTHONPATH=scripts
PYTHONPATH="D:/Taadaa/Tiktok-video/scripts" \
  "D:/CodexRuntime/tiktok-video/venv-core024/Scripts/python.exe" \
  -m pytest tests/test_tiktok_workflow.py -k "dismiss_popups_ui_dump or fingerprint_stale or fingerprint_fresh" --no-header -q
```

- Toàn bộ `tests/` (không filter) fail nếu thiếu `yt-dlp` — conftest import
  `source_pool_builder` → `SystemExit: Thieu yt-dlp`. Khi chỉ sửa state machine /
  fingerprint, chạy riêng `test_tiktok_workflow.py` (file không import source_pool_builder).
- `.pytest_cache` Permission denied warning là vô hại (venv chạy chéo quyền).
- Khi NÂNG automation-core version (vd 0.4.35 → 0.4.40): cập nhật
  `test_upload_launcher_pins_runtime_and_does_not_auto_login_requeue` assert version
  cùng lúc, nếu không suite fail.
