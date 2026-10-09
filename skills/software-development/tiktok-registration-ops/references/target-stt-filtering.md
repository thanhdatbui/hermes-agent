# Target STT Filtering in Tiktok_Reg Detection

## Usage
`select_pending_targets` in `scripts/tiktok_target_eligibility.py` and `detect_targets` in `_detect_clean.py` support filtering targets by specific machine STTs via `target_stts: Iterable[int] | None`.

### Python API
```python
import _detect_clean

# Lọc danh sách máy STT cụ thể
devices, source_rows, registered, targets, lock_rejections = _detect_clean.detect_targets(
    target_stts=[7, 9, 15]
)
```

### Environment Variable
`_detect_clean.detect_targets()` falls back to `os.environ["TIKTOK_REG_TARGET_STTS"]` if `target_stts` is not passed:
```bash
# Phân cách bằng dấu phẩy
TIKTOK_REG_TARGET_STTS="7, 9" python _detect_clean.py
```

### Low-level eligibility selector
```python
from scripts.tiktok_target_eligibility import select_pending_targets

pending = select_pending_targets(
    devices=devices,
    source_rows=source_rows,
    registered_mailboxes=registered,
    machine_account_counts=machine_counts,
    max_accounts_per_machine=8,
    target_stts=[7, 9],
)
```
