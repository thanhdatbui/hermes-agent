# Stale Proxy Readiness Timeout & Device Lock Bypass (2026-09-09)

## 1. Sự Cố Farm Alert & Triệu Chứng Hiện Trường
- **Quy trình / Script:** Chuỗi Ban Đêm Reg & 2FA (`night-chain-reg-pipeline` / `run_night_chain_pipeline.py`).
- **Triệu chứng lỗi:** Phase 3 (Add 2FA TikTok) kết thúc với exit code 4, báo động đỏ Farm Alert:
  ```text
  41 | 323 | m************* | failed | WORKER_CRASH: TimeoutError: proxy readiness timed out for ce031823f9b1903c01
  ```
- **Hậu quả:** Worker subprocess `run_capture_phase_b.py` trên máy 41 bị crash ở ngay bước tiền trạm (preflight), khiến `run_batch_live_2fa.py` đánh dấu kết quả `failed`, trả exit code 4 và kích hoạt chuông cảnh báo pipeline ban đêm.

---

## 2. Phân Tích Nguyên Nhân Gốc Rễ (Root Cause)

### 2.1. Cơ Chế Độc Quyền Máy và Bẫy `wait_for_proxy_ready`
Trong `run_capture_phase_b.py` (dòng 119–127), runner tiến hành chiếm quyền điều khiển thiết bị:
```python
lease = acquire_device_lock(
    machine=cfg.machine, serial=cfg.serial,
    project="tiktok-add-bao-mat-f2a", command="phase-b-live",
    user_authorized=True,
    allow_takeover=True,
    takeover_scope=os.environ.get("TAKEOVER_SCOPE", "OPERATOR_PREEMPT"),
    takeover_authorized=True,
    takeover_reason="operator live execution",
)
```
- Lời gọi này có `user_authorized=True` và `status="running"` (mặc định), nhưng **KHÔNG truyền `bypass_proxy_readiness=True`**.
- Khi `bypass_proxy_readiness` là `False`, `acquire_device_lock` trong `automation_core/device_lock.py` thực hiện:
  ```python
  if serial and not bypass_proxy_readiness and normalized_status != "queued":
      readiness_proof = wait_for_proxy_ready(
          serial,
          timeout=readiness_timeout,
          root=readiness_root,
          live_vpn_verifier=live_vpn_verifier,
      )
  ```
- Do `run_capture_phase_b.py` không truyền `live_vpn_verifier`, `live_vpn_verifier` mặc định là `None`.

### 2.2. Bản Ghi Rác Cũ 10 Ngày Trong `~/.codex/device-readiness/`
- `wait_for_proxy_ready(serial)` tính hash SHA-256 24 ký tự của serial `ce031823f9b1903c01` $\rightarrow$ `859cd1654e5bc969ec29ebca.json`.
- Trong thư mục `C:\Users\Kibe\.codex\device-readiness\`, file này thực tế đã tồn tại từ ngày 30/08/2026 với nội dung:
  ```json
  {
    "serial": "ce031823f9b1903c01",
    "state": "proxy_pending",
    "boot_id": "",
    "updated_at": "2026-08-30T03:48:29.408352+00:00"
  }
  ```
- Đây là tàn dư từ một phiên phục hồi proxy/reconnect (`device_recovery.py`) bị gián đoạn từ 10 ngày trước.
- Khi `wait_for_proxy_ready` đọc file:
  1. File tồn tại (`current is not None`).
  2. `state` là `"proxy_pending"` (khác `"proxy_ready"`).
  3. Không có tiến trình watcher nào chạy để chuyển state thành `"proxy_ready"`.
  4. `live_vpn_verifier` là `None` nên không có fallback probe.
  5. Hàm bị kẹt trong vòng lặp `while True: time.sleep(...)` suốt 180 giây cho đến khi cạn `deadline`, ném ra ngoại lệ:
     `TimeoutError: proxy readiness timed out for ce031823f9b1903c01`.

### 2.3. Sự Dư Thừa Tại Tầng Lock của Consumer
- Ngay sau khối `acquire_device_lock`, `run_capture_phase_b.py` (dòng 138–145) đã có sẵn cổng kiểm tra mạng fail-closed cực kỳ nghiêm ngặt:
  ```python
  from automation_core.preflight import (
      require_android_vpn, resolve_proxy_mapping_path,
      serial_is_mapped_in_workbook,
  )
  mapping = resolve_proxy_mapping_path()
  required = serial_is_mapped_in_workbook(
      mapping, cfg.serial, serial_headers=("phoneId", "deviceId", "serial"))
  require_android_vpn(adb, required=required)
  ```
- Cổng này trực tiếp kiểm tra giao diện `tun0`, trạng thái `NetworkAgentInfo` và cào IP thực qua `atx-agent curl`. Do đó, việc lock thiết bị bị nghẽn bởi handshake proxy readiness là hoàn toàn không cần thiết và tiềm ẩn rủi ro treo chéo.

---

## 3. Bản Vá Phòng Vệ Toàn Diện 3 Tầng (3-Tier Hardening)

### Tầng 1: Consumer Level (`run_capture_phase_b.py`)
Bổ sung tham số `bypass_proxy_readiness=True` vào lời gọi `acquire_device_lock`:
```python
lease = acquire_device_lock(
    machine=cfg.machine, serial=cfg.serial,
    project="tiktok-add-bao-mat-f2a", command="phase-b-live",
    user_authorized=True,
    allow_takeover=True,
    takeover_scope=os.environ.get("TAKEOVER_SCOPE", "OPERATOR_PREEMPT"),
    takeover_authorized=True,
    takeover_reason="operator live execution",
    bypass_proxy_readiness=True,
)
```
- Ngăn chặn lock thiết bị bị chặn bởi các watcher readiness bên ngoài.
- Để việc xác minh mạng cho `require_android_vpn(adb, required=required)` độc lập đảm nhiệm.

### Tầng 2: Control Plane Level (`automation_core/readiness.py`)
Gia cố hàm `wait_for_proxy_ready` với cơ chế phát hiện bản ghi cũ (stale check):
```python
def wait_for_proxy_ready(
    serial: str,
    boot_id: str = "",
    *,
    timeout: float = 180,
    poll_interval: float = 1,
    root=None,
    live_vpn_verifier: Callable[[str], bool] | None = None,
    max_stale_seconds: float = 600,
) -> dict | None:
```
- Nếu bản ghi trên đĩa có `state == "proxy_pending"` nhưng `updated_at` đã cũ hơn `max_stale_seconds` (mặc định 600s = 10 phút), và `live_vpn_verifier is None`:
  $\rightarrow$ Xem như bản ghi đã lỗi thời (stale marker), return `None` thay vì loop 180s rồi timeout crash tiến trình.

### Tầng 3: Disk Hygiene (`~/.codex/device-readiness/`)
- Dọn dẹp định kỳ / purge toàn bộ các file readiness tồn đọng có trạng thái `proxy_pending` cũ hơn 24 giờ.
