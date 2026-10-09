# Phân biệt ADB Transport Disconnect vs Missing Device Proxy Trong Preflight (2026-10-09)

## 1. Bản chất sự cố & Cạm bẫy False-Positive
* **Cạm bẫy:** Khi triển khai chốt chặn chống leak Direct IP trên Android (`settings get global http_proxy`), nếu thiết bị bị lỏng cáp USB, nghẽn hub USB, hoặc rớt khỏi `adb devices` (offline/unauthorized/not found):
  - Lệnh `adb.shell(["settings", "get", "global", "http_proxy"], check=False)` trả về `stdout=""` kèm mã lỗi exit code != 0 hoặc stderr chứa `device not found` / `device offline` / `adb command timed out`.
  - Nếu runner chỉ kiểm tra `val = stdout.strip(); if not val: raise ConsumerPreflightError("settings global http_proxy is missing or :0")`, lỗi mất kết nối phần cứng USB/ADB sẽ bị quy kết nhầm thành **"máy chưa gán proxy"**.
* **Hậu quả:** Gây báo động giả lỗi cấu hình proxy toàn dàn, khiến người vận hành tập trung kiểm tra proxy/Singbox/MobiProxy thay vì kiểm tra cáp hub USB hoặc restart daemon ADB.

## 2. Quy tắc cài đặt chuẩn (Fail-Fast Transport Disconnect Trước Device Proxy Check)
Trước khi đánh giá giá trị trả về của `settings get global http_proxy`, bắt buộc phải thẩm định tính toàn vẹn của kết nối ADB:

```python
device_proxy = None
p_res = None
p_err = ""
try:
    p_res = adb.shell(["settings", "get", "global", "http_proxy"], timeout=3.0, check=False)
    p_err = f"{getattr(p_res, 'stderr', '')}\n{getattr(p_res, 'stdout', '')}".strip()
    val = str(getattr(p_res, "stdout", "") or "").strip()
    if val and val not in ("null", ":0", "none"):
        device_proxy = val
except Exception as exc:
    p_err = str(exc)

# 1. BẮT BUỘC Fail-fast nếu transport disconnect / timeout
if is_connection_lost(p_err) or "timed out" in p_err.lower():
    raise ConsumerPreflightError(
        f"device is offline or ADB/USB disconnected for {serial}: {p_err}"
    )

# 2. CHỈ ĐÁNH GIÁ THIẾU PROXY khi lệnh shell thực thi thành công trên máy (ok=True / exit_code==0)
p_ok = False
if p_res is not None:
    p_ok_val = getattr(p_res, "ok", None)
    p_rc_val = getattr(p_res, "returncode", None)
    p_ec_val = getattr(p_res, "exit_code", None)
    if isinstance(p_ok_val, bool):
        p_ok = p_ok_val
    elif isinstance(p_rc_val, int):
        p_ok = (p_rc_val == 0)
    elif isinstance(p_ec_val, int):
        p_ok = (p_ec_val == 0)

if p_ok and not device_proxy:
    print(
        f"[PREFLIGHT_FAIL_CLOSED] [DEVICE_PROXY_MISSING] serial={serial} "
        f"reason=settings_global_http_proxy_empty_or_zero",
        flush=True,
    )
    raise ConsumerPreflightError(
        f"required Android VPN/proxy is not set on device: settings global http_proxy is missing or :0 for {serial}"
    )
```

## 3. Pitfalls liên quan đến Wi-Fi Intent & Subnet Matching
1. **Escape SSID có khoảng trắng trong `am start` Intent (`adb-join-wifi.apk`):**
   - Với SSID như `"kibe 1"`, `"kibe 2"`, `"admin 1"`:
   - Nếu truyền `-e ssid ssid` không bọc nháy kép, Android Intent receiver sẽ cắt chuỗi tại dấu cách (`kibe`), khiến máy quét tìm SSID `kibe` vô tận và không bao giờ kết nối được `kibe 1`.
   - BẮT BUỘC bọc nháy kép: `-e ssid f'"{ssid}"'`.
2. **Subnet Matching trong Wi-Fi Auto-Healer:**
   - Khi quét kiểm tra IP `wlan0`: Regex `inet 192.168.` sẽ bắt trúng cả dải VLAN 10 (`192.168.10.x`) cấp bởi router phụ hoặc MikroTik untagged.
   - BẮT BUỘC dùng regex chặt: `r"inet\s+(192\.168\.110\.\d+)"` để đảm bảo thiết bị thực sự kết nối vào subnet sản xuất của Farm.
