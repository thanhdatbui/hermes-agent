# Pre-Session Gate Framework Blindspot & Service Check Resolution (2026-10-22)

## 1. Bối Cảnh Sự Cố & Hiện Trường
- **Sự cố Máy 213 (Ca 2 Chiều 22/10/2026):**
  - Watchdog báo cáo: Máy 213 thuộc nhóm "Mất kết nối Wi-Fi (AP)".
  - Trích xuất hiện trường O(1) qua `inspect_machine.py 213`:
    * Wi-Fi IP vẫn nhận bình thường (`192.168.110.87` cấp từ MikroTik DHCP).
    * Khi đọc proxy qua `settings get global http_proxy`, thiết bị trả về:
      `cmd: Can't find service: settings`
    * Lớp Android Java framework (`system_server` / `servicemanager`) bị crash/treo ngầm, trong khi tiến trình daemon Linux kernel `adbd` vẫn kết nối.
  - Watchdog quét lỗi proxy/mạng không xác định nên gom nhầm vào danh mục "Mất kết nối Wi-Fi (AP)".

---

## 2. Bản Chất Điểm Mù Hệ Thống & Câu Hỏi "Tại Sao Lúc Vận Hành Không Cứu?"

1. **Điểm mù Pre-Session Device Gate (`pre_session_device_gate.py`):**
   - Trước ca chạy, gate chỉ kiểm tra nhanh bằng lệnh:
     `adb -s <serial> get-state`
   - Tiến trình `adbd` chạy độc lập dưới kernel Linux C space. Khi `system_server` chết, `adbd` vẫn bắt tay hoàn hảo và trả về `device`.
   - Gate nhận `device` nên kết luận máy `ready` 100%, đưa thẳng vào danh sách dispatch mà không kích hoạt quy trình cứu hộ trước ca.

2. **Kỷ luật In-Flight Fail-Fast trong ca nuôi:**
   - Trong lúc ca đang chạy, `vpn_preflight.py` chỉ hỗ trợ cứu hộ nhẹ Level 3 Reconnect (`adb reconnect` để bắt tay lại gói USB `A_SYNC`). Lệnh này hoàn toàn vô hiệu với `system_server` đã crash.
   - Để cứu `Can't find service: settings`, bắt buộc phải reboot máy điện thoại (Level 2 bypass-shell reboot).
   - Khởi động lại Samsung S7 mất **45–60 giây**. Nếu worker tự ý reboot điện thoại giữa chừng sẽ làm nghẽn worker thread, trượt timeout của batch, và gây bão DHCP/nghẽn I/O bus USB 2.0 EHCI.
   - Do đó runner bắt buộc tuân thủ Fail-Fast: ngắt máy lỗi để giải phóng worker cho các máy tiếp theo trong Row.

---

## 3. Giải Pháp Vá Chuẩn Hóa 2 Tầng (`pre_session_device_gate.py`)

Thăm dò 2 tầng kết hợp (Kernel ADB + Java Framework Service Check):
```python
res = run_subprocess(cmd, timeout=timeout)
state = res.stdout.strip()
if res.returncode == 0 and state == "device":
    framework_cmd = base_cmd + ["shell", "service", "check", "settings"]
    f_res = run_subprocess(framework_cmd, timeout=min(2.0, timeout))
    if f_res.returncode == 0 and "not found" not in f_res.stdout.lower() and f_res.stdout.strip():
        return True, "device"
    err = f_res.stderr.strip() or f_res.stdout.strip() or "framework_unresponsive"
    return False, f"framework_unresponsive: {err}"
```

### Lợi ích vận hành:
1. **Bắt trúng framework crash:** Khi `settings` service bị mất, probe trả về `(False, "framework_unresponsive: ...")`.
2. **Kích hoạt cứu hộ trước ca:** `probe_and_recover_device()` phát hiện `False` ngoài khung giờ blackout sẽ gọi ngay `recover_stuck_s7.py` (Level 1 soft ping fail -> tự động leo thang Level 2 direct daemon reboot `adb -s <serial> reboot`).
3. **Nghiệm thu trước khi giao việc:** Máy được reboot xong, framework nạp lại đầy đủ thì re-probe mới chuyển `recovered` và đưa vào ca nuôi. Nếu vẫn chết thì loại ra ngoài batch (`recovery_failed`), bảo vệ tỷ lệ thành công của phiên.
4. **Hiệu năng cực nhanh:** `service check settings` chỉ tốn ~0.2s trên thiết bị thật, không làm chậm nhịp khởi động ca.
