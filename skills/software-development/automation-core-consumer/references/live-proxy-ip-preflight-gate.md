# Chốt chặn xác thực Proxy Live IP trong Farm Consumers (Gmail, TikTok)

## 1. Bối cảnh & Nguyên tắc Fail-Closed
Trong các worker runner tự động hoá Android farm (Gmail Reg, TikTok Reg, TikTok Login, Follow...):
- Thiết bị có thể báo VPN tunnel `tun0` hoặc interface `wlan0` ở trạng thái UP, nhưng proxy chết, router proxy đứt kết nối, hoặc IP egress thực tế chưa thông.
- Nếu không kiểm tra nghiêm ngặt `proxy_ip` (public IP egress đã được probe thực tế từ thiết bị), worker sẽ vào luồng reg/login bằng IP nội bộ hoặc rớt mạng giữa chừng, gây tốn quota tài khoản hoặc dính bot-check.
- Do đó, mọi consumer bắt buộc phải có chốt chặn fail-closed: **có gán proxy mapping (`required=True`) thì bắt buộc phải xác thực được `proxy_ip` sống (non-empty)**.

---

## 2. Tiêu chuẩn triển khai chuẩn trong Runner

### A. Trong vòng lặp hậu reboot (`verify_vpn_after_reboot`)
Khi thiết bị reboot để khôi phục trạng thái, hàm kiểm tra VPN phải truyền `verify_live_ip=True` và từ chối nếu không có `proxy_ip`:

```python
def verify_vpn_after_reboot():
    required = serial_is_mapped_in_workbook(
        VICHANGER_PROXY_MAPPING_PATH,
        device_id,
        serial_headers=VICHANGER_SERIAL_HEADERS,
    )
    try:
        status = require_android_vpn(adb, required=required, verify_live_ip=True)
        if required and not str(getattr(status, "proxy_ip", "") or "").strip():
            return False
        return bool(status.allowed)
    except ConsumerPreflightError:
        return False
```

---

### B. Trong khối Preflight chính (`[vichanger-preflight]`) trước khi vào Task
Ở entrypoint chính (trước khi tạo tài khoản, sinh account hoặc chạy action):
1. Gọi `require_android_vpn(..., verify_live_ip=True)`.
2. Kiểm tra chặt chẽ:
   - `vpn_status.allowed`
   - `vpn_status.connected`
   - `proxy_ip` không rỗng nếu `vpn_required=True`
3. Bắt `ConsumerPreflightError`:
   - Ghi log chuẩn `❌ STOPPED: [PREFLIGHT_PROXY] {exc}` để các orchestrator launcher (`run_parallel.ps1`, batch monitor) nhận diện chính xác lý do dừng.
   - Ghi log `[vichanger-preflight] BLOCKED machine={stt:02d} serial={device}: {exc}`.
   - Giải phóng device lock an toàn với `device_lock.finish(succeeded=False, failure_status="handoff")`.
   - Thoát với exit code `2`.

```python
try:
    vpn_required = serial_is_mapped_in_workbook(
        VICHANGER_PROXY_MAPPING_PATH,
        device,
        serial_headers=VICHANGER_SERIAL_HEADERS,
    )
    vpn_status = require_android_vpn(
        AdbClient(adb_path=ADB_EXE, serial=device, default_timeout=20),
        required=vpn_required,
        verify_live_ip=True,
    )
    status_res = getattr(vpn_status, "result", str(vpn_status)).upper()
    proxy_ip = str(getattr(vpn_status, "proxy_ip", "") or "").strip()
    if vpn_required and (
        not getattr(vpn_status, "allowed", False)
        or not getattr(vpn_status, "connected", False)
        or not proxy_ip
    ):
        evidence = getattr(vpn_status, "error", "") or "live proxy IP proof missing"
        raise ConsumerPreflightError(f"VPN verification failed: {evidence}")
    log(f"[vichanger-preflight] {status_res} proxy_ip={proxy_ip}")
except ConsumerPreflightError as exc:
    log(f"❌ STOPPED: [PREFLIGHT_PROXY] {exc}")
    log(f"[vichanger-preflight] BLOCKED machine={stt:02d} serial={device}: {exc}")
    device_lock.finish(succeeded=False, failure_status="handoff")
    sys.exit(2)
```

---

## 3. Checklist kiểm chứng (Verification Checklist)
1. **Mock Test Offline**:
   - `vpn_required=True, proxy_ip=""`: Phải kích hoạt `ConsumerPreflightError`, in log `❌ STOPPED: [PREFLIGHT_PROXY]`, release lock `handoff`, exit `2`.
   - `vpn_required=True, proxy_ip="x.x.x.x"`: Cho phép luồng tiếp tục, log `[vichanger-preflight] CONNECTED proxy_ip=x.x.x.x`.
   - `vpn_required=False`: Bỏ qua kiểm tra IP (`allowed=True`), không crash.
2. **Compile Test**: `python -m py_compile <runner.py>` phải exit 0.
