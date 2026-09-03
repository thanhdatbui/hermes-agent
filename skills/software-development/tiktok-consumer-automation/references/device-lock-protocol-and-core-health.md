# Device lock protocol v1 legacy + cross-project reclaim

## Lock protocol v2 takeover guard

`automation_core.device_lock._takeover_payload` từ chối reclaim khi:

1. `owner.get("host") != current_host` → không cùng máy.
2. `owner.get("lock_protocol_version") != _LOCK_PROTOCOL_VERSION` (hiện = 2).
   **Lock v1 legacy (`lock_protocol_version: None`/missing) KHÔNG reclaim được**
   qua core dù PID dead, dù `allow_takeover=True, takeover_scope=FULL_SCOPE_TAKEOVER`.
   → `DeviceLockUnavailable: device lock active: path=... machine_N.lock.json`.
3. Owner còn sống (`alive is not False`) với status active → không reclaim.

## Phân loại lock trước khi quyết định

```bash
python -c "import json; d=json.load(open('machine_N.lock.json')); print(d.get('lock_protocol_version'), d.get('project'), d.get('pid'), d.get('status'), d.get('owner_active'))"
```

- **protocol v2 + PID dead + cùng project `Tiktok_Reg`** → `--full-scope-takeover`
  reclaim được qua core (chạy runner với flag).
- **protocol v1 legacy (`None`) + PID dead + project ≠ tiktok-upload** (user đã
  cho phép giành trừ `tiktok-upload`) → core từ chối; xử lý thủ công an toàn:
  backup file vào `backup_takeover_<date>/`, xoá cả `machine_N.lock.json` VÀ
  `serial_<serial>.lock.json` (2 file, đừng quên serial lock — runner vẫn báo
  `DEVICE_LOCKED: path=serial_...` nếu chỉ xoá machine lock). Verify PID dead
  trước (`kill -0 <pid>` → DEAD).
- **project `tiktok-upload`** → GIỮ NGUYÊN theo lệnh user (lock cross-project
  của upload pipeline, không reclaim).

## Reclaim qua core (protocol v2, PID dead)

```python
from automation_core.device_lock import acquire_device_lock, FULL_SCOPE_TAKEOVER
lease = acquire_device_lock(
    machine=stt, serial=serial, project="Tiktok_Reg",
    command=["tiktok-recovery-new-handler", str(stt), "reclaim"],
    status="queued", run_id="reclaim-<ts>",
    allow_takeover=True, takeover_scope=FULL_SCOPE_TAKEOVER,
    takeover_authorized=True,
    takeover_reason="operator authorized reclaim of dead cross-project lock (not tiktok-upload)",
    bypass_proxy_readiness=True,
)
```

## Checklist khi run báo DEVICE_LOCKED

1. Đọc lock JSON: project? protocol version? pid alive?
2. PID dead + protocol v2 + cùng project → runner `--full-scope-takeover`.
3. PID dead + protocol v1 + project được phép → backup + xoá thủ công 2 file.
4. Project `tiktok-upload` hoặc pid ALIVE → giữ nguyên, skip.

## Hotmail/Outlook health check — module core `automation_core.outlook_health`

Tạo theo pattern `google_health.py` (consumer cung cấp adapter mỏng, core giữ
state machine):

- `run_outlook_health_check(callbacks, max_steps, max_state_repeats)` —
  `open_inbox` → `read_ui` → `classify_ui`; trả `OutlookHealthResult(status,
  reason, xml)`.
- Status: `HEALTH_NORMAL` (inbox live), `HEALTH_RELOGIN` (sign-in form persists),
  `HEALTH_LOCKED`, `HEALTH_MANUAL`, `HEALTH_UNKNOWN` (budget exhausted).
- Consumer xoá mail (source + device) CHỈ khi RELOGIN/LOCKED; NORMAL không bao
  giờ cleanup — mirror Gmail CAPTCHA contract.
- Classifier: flatten CẢ XML blob (nhãn nằm trong attribute), NFKD strip dấu +
  `replace("đ","d")`; markers cả tiếng Việt lẫn Anh.
- Test: `tests/test_outlook_health.py` (7 tests: live, relogin, locked,
  unknown-budget, classifiers). Core suite 443 passed.
- Bump version core + ghi contract vào `docs/ui-compatibility-contract.md`.

## Test core KHÔNG đụng env runner

Chạy core tests bằng `PYTHONPATH=<core>/src`, KHÔNG `pip install -e .`. Editable
install ghi đè wheel đã pin (0.4.31) → runner kế tiếp vỡ
`cannot import name 'AndroidTransportRecoveryError'`. Fix: `--force-reinstall
--no-deps <wheel đúng pin>`.
