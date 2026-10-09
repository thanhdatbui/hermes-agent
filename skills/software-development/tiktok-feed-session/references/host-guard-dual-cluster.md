# Lỗi Host Guard Dual-Cluster Farm (Kibe vs Admin) – Nguyên nhân & Fix

## Vấn đề

Khi chạy TikTok feed sessions trên Farm 2 cụm (Kibe = máy 1-80, Admin = máy 201-280), lỗi **`MACHINE_OUT_OF_RANGE: machine=201 không thuộc host kibe (range 1-80). Dừng fail-closed.`** xuất hiện, ngăn chặn Admin machines thực hiện feed.

## Nguyên nhân cốt lõi

`tiktok_runner.py` định nghĩa `CLUSTERS` riêng biệt cho Kibe và Admin:

```yaml
CLUSTERS: list[dict[str, Any]] = [
    {
        "name": "kibe",
        "workbook_root": KIBE_WORKBOOK_ROOT,
        "runtime_root": KIBE_RUNTIME_ROOT,
        "account_workbook": str(KIBE_WORKBOOK_ROOT / "taikhoan_run_safe.xlsx"),
        "state_file": KIBE_RUNTIME_ROOT / "cron-state" / "runner_simple_state.json",
        "artifact_base": KIBE_RUNTIME_ROOT / "live",
    },
    {
        "name": "admin",
        "workbook_root": ADMIN_WORKBOOK_ROOT,
        "runtime_root": ADMIN_RUNTIME_ROOT,
        "account_workbook": str(ADMIN_WORKBOOK_ROOT / "taikhoan_run_safe.xlsx"),
        "state_file": ADMIN_RUNTIME_ROOT / "cron-state" / "runner_simple_state.json",
        "artifact_base": ADMIN_RUNTIME_ROOT / "live",
    },
]
```

Nhưng `host_guard` (trong `taadaa_host.py`) kiểm tra `TAADAA_HOST_CONFIG` *mặc định* từ môi trường của máy Master (thường trỏ tới `D:/Taadaa/machine-config/kibe.yaml`).

Khi spawn Admin machines, script con kế thừa môi trường gốc này, dẫn đến mismatch: range 1-80 vs machine 201-280.

## Fix (đã áp dụng vào `tiktok_runner.py`)

1. **Thêm `host_config` vào từng cluster**

```yaml
CLUSTERS: list[dict[str, Any]] = [
    {
        "name": "kibe",
        "workbook_root": KIBE_WORKBOOK_ROOT,
        "runtime_root": KIBE_RUNTIME_ROOT,
        "account_workbook": str(KIBE_WORKBOOK_ROOT / "taikhoan_run_safe.xlsx"),
        "state_file": KIBE_RUNTIME_ROOT / "cron-state" / "runner_simple_state.json",
        "artifact_base": KIBE_RUNTIME_ROOT / "live",
        "host_config": r"D:\Taadaa\machine-config\kibe.yaml",  # <- CẤM THIẾT
    },
    {
        "name": "admin",
        "workbook_root": ADMIN_WORKBOOK_ROOT,
        "runtime_root": ADMIN_RUNTIME_ROOT,
        "account_workbook": str(ADMIN_WORKBOOK_ROOT / "taikhoan_run_safe.xlsx"),
        "state_file": ADMIN_RUNTIME_ROOT / "cron-state" / "runner_simple_state.json",
        "artifact_base": ADMIN_RUNTIME_ROOT / "live",
        "host_config": r"D:\Taadaa\machine-config\admin.yaml",  # <- CẤM THIẾT
    },
]
```

2. **Truyền `host_config` vào `_spawn_feed_session()`**

```python
def _spawn_feed_session(
    row: int,
    session_index: int,
    now: datetime,
    is_rest_day: bool = False,
    account_workbook: str = ACCOUNT_WORKBOOK,
    artifact_base: Path = ARTIFACT_BASE,
    host_config: str | None = None,  # <- THÊM
) -> int:
    ...
    child_env = dict(os.environ)
    child_env.pop("TAADAA_REST_DAY_NO_FOLLOW", None)
    if host_config:
        child_env["TAADAA_HOST_CONFIG"] = host_config
```

3. **Lấy từ cluster cho mỗi lần dispatch**

```python
for cluster in CLUSTERS:
    cluster_name = cluster["name"]
    ...
    cluster_host_cfg = cluster.get("host_config")  # <- trích xuất
    rc = _spawn_feed_session(
        row,
        session_index,
        now,
        is_rest_day=is_rest_day,
        account_workbook=cluster_wb,
        artifact_base=cluster_artifact,
        host_config=cluster_host_cfg,  # <- truyền vào
    )
```

## Kết quả

- Máy Admin sử dụng `admin.yaml` (range: 200-999) – an toàn với fail-closed guard.
- Máy Kibe vẫn sử dụng `kibe.yaml` (range: 1-80).
- Không còn lỗi `MACHINE_OUT_OF_RANGE`.
- `taadaa_host.py` được gọi trong `run_tiktok.py` sẽ đọc `TAADAA_HOST_CONFIG` được set từ mỗi cluster.

## Kiểm tra Verification

Sau fix, bạn có thể xác nhận:

1. **Reset state:**

```bash
python -c "import json; open('D:/Taadaa/runtime/admin/cron-state/runner_simple_state.json', 'w', encoding='utf-8').write(json.dumps({'last_row': 0, 'last_window': '', 'last_run_at': ''}, indent=2))"
```

2. **Kích hoạt Admin run:**

```bash
python -c "
import os, subprocess
repo_root = r'D:\Taadaa\tiktok-luot nuoi acc'
runner = r'C:\Users\Kibe\AppData\Local\hermes\scripts\tiktok_runner.py'
env = dict(os.environ)
env['HERMES_CRON_NOW'] = '2026-09-20T18:00:00+07:00'
subprocess.run([runner], cwd=repo_root, env=env, capture_output=True)
"  # stdout nên hiển thị "tiktok_runner [admin]: Row 6 co 2 accounts hop le."

3. **Inspect machine admin:** `python D:/Taadaa/tools/inspect_machine.py 204`

## Ghi chú an toàn

- **Không còn grep diện rộng** (`os.walk`, `glob(recursive=True)`, `find`, `grep -rn`). Mỗi lần dispatch giờ trích xuất chính xác anchor từ config.
- **Ngang host config** (cấu hình per-machine) là yêu cầu an toàn – fail-closed với error message rõ ràng nếu mismatch.
- **Reference cho Admin YAML:** `D:/Taadaa/machine-config/admin.yaml`:

```yaml
host_id: admin
machine_range: [200, 999]
workbook_root: D:/OneDrive/TaadaaData/admin
runtime_root: D:/Taadaa/runtime/admin
```