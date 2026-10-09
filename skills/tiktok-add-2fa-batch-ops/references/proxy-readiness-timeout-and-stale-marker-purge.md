# Proxy Readiness Timeout & Stale Marker Purge (09/09/2026)

## 1. Sự cố Hiện trường (Farm Alert 09/09/2026)
- **Quy trình:** Chuỗi Ban Đêm Reg & 2FA (`night-chain-reg-pipeline` / `run_night_chain_pipeline.py`).
- **Triệu chứng:** Phase 3 (Add 2FA TikTok) kết thúc với `exit_code=4`:
  ```
  41 | 323 | m************* | failed | WORKER_CRASH: TimeoutError: proxy readiness timed out for ce031823f9b1903c01
  ```
- **Hậu quả:** Tiến trình worker subprocess `run_capture_phase_b.py` bị sập (exit code 1). `run_batch_live_2fa.py` bắt được crash và đánh dấu target row 323 máy 41 là `failed`, trả về `exit_code=4` làm toàn bộ pipeline chuỗi đêm Phase 3 bắn alert báo động.

## 2. Phân tích Nguyên nhân Gốc rễ (Root Cause)
1. **Thiếu cờ bypass trong runner Phase B:**
   - Trong `python_runner/run_capture_phase_b.py`, hàm `acquire_device_lock(...)` được gọi với `user_authorized=True` nhưng thiếu cờ `bypass_proxy_readiness=True`.
   - Trong `automation_core/device_lock.py`, khi `bypass_proxy_readiness=False` và `normalized_status != "queued"`, hàm tự động gọi `wait_for_proxy_ready(serial=serial, timeout=180)`.
2. **Bản ghi readiness mốc trong `~/.codex/device-readiness/`:**
   - Tệp `~/.codex/device-readiness/859cd1654e5bc969ec29ebca.json` (SHA-256 24 ký tự của serial `ce031823f9b1903c01` máy 41) tồn đọng từ ngày 30/08/2026 với nội dung:
     ```json
     {
       "serial": "ce031823f9b1903c01",
       "state": "proxy_pending",
       "boot_id": "",
       "updated_at": "2026-08-30T03:48:29.408352+00:00"
     }
     ```
   - Do tệp này có `state == "proxy_pending"`, và không có tiến trình proxy watcher/reconnect nào chạy từ 10 ngày trước để chuyển sang `proxy_ready`, đồng thời `live_vpn_verifier` truyền vào là `None`, `wait_for_proxy_ready` bị kẹt vòng lặp poll 180 giây rồi ném `TimeoutError`.
3. **Thừa thãi tầng kiểm tra tại device lock:**
   - Bản thân `run_capture_phase_b.py` đã có cổng kiểm tra VPN fail-closed độc lập ở ngay sau khi lấy lock:
     ```python
     mapping = resolve_proxy_mapping_path()
     required = serial_is_mapped_in_workbook(mapping, cfg.serial, serial_headers=("phoneId", "deviceId", "serial"))
     require_android_vpn(adb, required=required)
     ```
   - Việc handshake proxy readiness ở tầng `acquire_device_lock` chỉ nhằm phục vụ flow reboot/reconnect watcher, hoàn toàn không cần thiết cho luồng 2FA độc lập và dễ bị block bởi các marker cũ.

## 3. Bản vá & Khắc phục Chuẩn (Hai Tầng Phòng Thủ)

### Tầng 1: Hardening Runner Phase B (`tiktok-add-bao-mat-f2a`)
Trong `python_runner/run_capture_phase_b.py`:
```python
lease = acquire_device_lock(
    machine=cfg.machine, serial=cfg.serial,
    project="tiktok-add-bao-mat-f2a", command="phase-b-live",
    user_authorized=True,
    bypass_proxy_readiness=True,
    allow_takeover=True,
    takeover_scope=os.environ.get("TAKEOVER_SCOPE", "OPERATOR_PREEMPT"),
    takeover_authorized=True,
    takeover_reason="operator live execution",
)
```

### Tầng 2: Hardening Automation Core (`automation-core`)
Trong `src/automation_core/readiness.py`:
- Thêm hàm helper `_is_stale_marker(current, max_stale_seconds=600)` tính độ tuổi của trường `updated_at`.
- Trong `wait_for_proxy_ready`: nếu marker là `proxy_pending` và cũ hơn `max_stale_seconds` (mặc định 10 phút = 600s), đồng thời `live_vpn_verifier is None`, coi là marker mốc của tiến trình đã chết trong quá khứ $\rightarrow$ tự động bỏ qua và trả về `None` thay vì kẹt timeout 180s.

### Tầng 3: Dọn dẹp tệp rác hệ thống
- Xóa file `859cd1654e5bc969ec29ebca.json` của máy 41.
- Thanh lọc toàn bộ các tệp `.json` trong `~/.codex/device-readiness/` có `state == "proxy_pending"` cũ hơn 24 giờ.

## 4. Verification Checklist
1. `pytest python_runner/tests/test_run_capture_phase_b.py` $\rightarrow$ 5/5 pass.
2. `pytest tests/test_readiness.py` trong `automation-core` $\rightarrow$ 8/8 pass.
3. Test dry-run: `python python_runner/run_batch_live_2fa.py --rows 323 --adb-path "C:\Program Files (x86)\xiaowei\tools\adb.exe"` $\rightarrow$ `frozen | dry-run`, `exit_code=0`.
4. Test probe lock máy 41: `acquire_device_lock(machine=41, serial='ce031823f9b1903c01', ..., bypass_proxy_readiness=True)` phản hồi trong 0.1s.
