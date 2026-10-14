# ADB Dumpsys Bloat & VPN Preflight Timeout Triage (2026-10-14)

## 1. Triệu chứng hiện trường (Symptoms)
- Hàng loạt máy (30–60 máy trên cả 2 cụm Kibe và Admin) bị văng/hủy phiên nuôi acc đồng loạt:
  - Nhóm 1: `blocked-proxy-vpn` kèm lý do `device is offline or ADB/USB disconnected: adb command timed out ('settings', 'get', 'global', 'http_proxy')` hoặc `device not found`.
  - Nhóm 2: `prepare-tiktok failed to focus TikTok after launch` (quá 10 attempts không thấy package TikTok dù TikTok đã mở).
- Khi kiểm tra ngay sau phiên bằng `inspect_machine.py`, thiết bị hoàn toàn ONLINE, pin khỏe (>75%), không hề rớt phần cứng thực sự.

## 2. Nguyên nhân gốc rễ (Root Cause)

### A. Timeout kiểm tra proxy trong `vpn_preflight.py` quá ngắn (3.0s)
- Lệnh `adb.shell(["settings", "get", "global", "http_proxy"], timeout=3.0, check=False)` được gọi trước khi chạy phiên trên mỗi máy.
- Khi farm chạy tải cao (25–30 workers song song) hoặc qua mạng LAN tới Admin PC (`192.168.110.119:5037`), hàng đợi ADB daemon bị delay >3 giây.
- Exception timeout bị bắt và quy chụp thành `ConsumerPreflightError: device is offline or ADB/USB disconnected`, khiến hàng chục máy bị đánh dấu `blocked-proxy-vpn` và hủy phiên oan từ trước khi mở app.

### B. Nghẽn bus ADB do `dumpsys window` thô trong `observe.py`
- Trong `get_focused_activity()`, danh sách lệnh fallback chứa:
  ```python
  candidates = [
      ["dumpsys", "window", "displays"],
      ["dumpsys", "window"],                # XUẤT 3MB TEXT THÔ QUA USB!
      ["dumpsys", "activity", "activities"],# XUẤT 2MB TEXT THÔ QUA USB!
  ]
  ```
- Mỗi lần gọi `dumpsys window` hoặc `dumpsys activity activities` đẩy 2–3MB text qua cáp USB.
- Với 30 workers chạy đồng loạt, mỗi máy gọi `get_focused_activity` tới 10 lần trong vòng lặp focus check, tạo ra hàng gigabyte text dumpsys thô dồn dập vào ADB server daemon.
- Daemon ADB bị nghẽn (stall) lên tới 8 phút cho một lệnh, làm cho các lệnh `settings get global http_proxy` của máy khác cũng bị timeout lây chéo, và máy bị fast-fail vì hết thời gian chờ focus.

## 3. Bản vá chuẩn hóa (Standard Fix Pattern)

### A. Tăng timeout & retry cho `vpn_preflight.py`
```python
    device_proxy = None
    p_res = None
    p_err = ""
    for _attempt in range(2):
        try:
            p_res = adb.shell(["settings", "get", "global", "http_proxy"], timeout=8.0, check=False)
            p_err = f"{getattr(p_res, 'stderr', '')}\n{getattr(p_res, 'stdout', '')}".strip()
            val = str(getattr(p_res, "stdout", "") or "").strip()
            if val and val not in ("null", ":0", "none"):
                device_proxy = val
            break
        except Exception as exc:
            p_err = str(exc)
            if _attempt == 0 and ("timed out" in p_err.lower() or is_connection_lost(p_err)):
                time.sleep(1.0)
                continue
            break
```

### B. Lọc trên thiết bị (On-Device Grep) thay vì dump thô trong `observe.py`
```python
    candidates = [
        ["dumpsys", "window", "displays"],
        ["sh", "-c", "dumpsys window | grep -E 'mCurrentFocus|mFocusedApp|mFocusedWindow|mTopFullscreenOpaque'"],
        ["dumpsys", "activity", "recents"],
    ]
    dumpsys_timeout = min(8.0, float(ctx.timeout("adb_seconds", 15)))
```
- Lọc `grep` trực tiếp trên máy Android chỉ truyền đúng 2 dòng text qua cáp USB thay vì 3MB dump thô, giảm 99.9% lưu lượng bus ADB.

## 4. Quy tắc nghiệm thu (Verification Rule)
- Chạy focused tests:
  ```bash
  pytest python_runner/tests/test_device_prepare.py python_runner/tests/test_multi_machine_fast_fail.py -q
  pytest python_runner/tests/test_vpn_preflight_router.py -k "test_require_proxy_connected_passes_adb_to_proxy_server_live or test_offline_device_raises_usb_disconnected_without_recovery_integration" -q
  ```
- Kiểm tra thiết bị 2 cụm: `python D:/Taadaa/tools/inspect_machine.py`.
