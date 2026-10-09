# ADB Transport Disconnect vs Missing Device Proxy Preflight Triage (2026-10-09)

## 1. Hiện Tượng & Triệu Chứng Cảnh Báo
* **Triệu chứng:** Hàng loạt máy farm báo lỗi:
  ```text
  required Android VPN/proxy is not set on device: settings global http_proxy is missing or :0 for <serial>
  ```
* **Cạm bẫy chẩn đoán sai:** Người vận hành hoặc agent suy diễn là máy bị reset proxy hoặc mất file cấu hình proxy, vội vã chạy lại script gán proxy.
* **Thực tế hiện trường:** Proxy trên thiết bị Android (`192.168.110.2:200xx`) vẫn nguyên vẹn 100%. Lỗi thực sự là cáp USB bị lỏng hoặc ADB transport socket trên host bị kẹt/deadlock, khiến lệnh `adb.shell(["settings", "get", "global", "http_proxy"])` không thể kết nối tới thiết bị và trả về stdout rỗng `""`.

---

## 2. Phân Tích Kỹ Thuật (Root Cause)

1. **Khuyết tật logic trong guard kiểm tra proxy (commit 2026-10-08):**
   ```python
   p_res = adb.shell(["settings", "get", "global", "http_proxy"], timeout=3.0, check=False)
   val = str(getattr(p_res, "stdout", "") or "").strip()
   if val and val not in ("null", ":0", "none"):
       device_proxy = val
   if not device_proxy:
       raise ConsumerPreflightError(f"settings global http_proxy is missing or :0 for {serial}")
   ```
   Khi máy bị offline (`error: device offline`) hoặc rớt khỏi bus USB (`device '...' not found`):
   - `p_res.stdout` trả về rỗng `""`.
   - `p_res.stderr` chứa chuỗi báo mất kết nối ADB.
   - Code bắt chuỗi rỗng và ngộ nhận là thiết bị online nhưng proxy bị `:0`, ném lỗi sai lệch hoàn toàn so với hiện trường.

2. **Cạm bẫy thuộc tính `AdbResult` vs `subprocess.CompletedProcess`:**
   - Trong `automation-core`, class `AdbResult` sử dụng các trường `ok: bool` và `exit_code: int`.
   - `AdbResult` KHÔNG CÓ trường `returncode`.
   - Dùng `getattr(p_res, "returncode", 0) == 0` sẽ luôn trả về `True` (do default 0), làm sai lệch mọi nhánh kiểm tra thành công/thất bại của mock ADB và subprocess.

---

## 3. Quy Chuẩn Triển Khai Bắt Buộc (Fail-Fast Invariant)

Trong mọi consumer preflight (`python_runner/core/vpn_preflight.py`):
1. **Bắt buộc kiểm tra `is_connection_lost` trước:**
   ```python
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

   if is_connection_lost(p_err) or "timed out" in p_err.lower():
       raise ConsumerPreflightError(
           f"device is offline or ADB/USB disconnected for {serial}: {p_err}"
       )
   ```
2. **Chỉ assert `missing or :0` khi lệnh thực thi thành công trên máy (`p_ok == True`):**
   ```python
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
       raise ConsumerPreflightError(
           f"required Android VPN/proxy is not set on device: settings global http_proxy is missing or :0 for {serial}"
       )
   ```

---

## 4. Quy Trình Khôi Phục Nhanh Khi Hàng Loạt Máy Mất ADB (Triage O(1))

1. Chạy `adb devices` kiểm tra trạng thái:
   - Nếu thấy máy ở trạng thái `offline`: chạy `adb reconnect offline` lập tức đưa máy về `device`.
   - Nếu nhiều máy biến mất khỏi danh sách: chạy reset ADB daemon:
     `adb kill-server && adb start-server && adb devices`
     Giải phóng socket transport bị deadlock, phục hồi ngay 80–90% các máy bị kẹt.
2. Đối soát lại với file `PROXYgandienthoai.xlsx` để xác định chính xác các máy thực sự bị lỏng cáp vật lý / tắt nguồn (chỉ cần can thiệp tay các máy còn sót lại).
