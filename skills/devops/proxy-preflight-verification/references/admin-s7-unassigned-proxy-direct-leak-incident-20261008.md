# Admin S7 Unassigned Global Proxy & Direct IP Leak Incident (2026-10-08)

## 1. Hiện tượng & Báo động từ User
- **Hiện tượng:** Cụm proxy MikroTik Admin (`mirotik1.taadaa.click:10001..10035` / `192.168.110.2:10008..10035`) sập hoàn toàn / timed out 100%. User chụp màn hình app Jiwei thấy dàn máy Farm Admin (máy 201–280) vẫn đang mở TikTok lướt feed, load video ầm ầm.
- **Câu hỏi của User:** *"Proxy admin đang mất mạng tại sao script được phép chạy trên S7 admin?"*

## 2. Nguyên nhân kỹ thuật (Root Cause 2 Tầng)

### Tầng 1: Máy S7 Admin chưa từng được gán proxy ADB vào hệ điều hành
- Lệnh kiểm tra trên các máy thật S7 Admin (`ce031603fb1ca82704`, `99afb048`, `ce021602a92d1a0d04`):
  ```bash
  adb -s <serial> shell settings get global http_proxy
  # Kết quả: :0 (hoặc chuỗi rỗng)
  ```
- Dù file quy hoạch `D:\OneDrive\TaadaaData\admin\PROXYgandienthoai.xlsx` có map serial với cổng MikroTik `10008..10035`, nhưng thực tế trên máy S7 chưa được chạy script gán proxy `D:\Taadaa\AI-Tools\scripts\set_proxy_farm_admin_adb.py` (hoặc từng bị chạy cờ `--clear`).

### Tầng 2: Cạm bẫy Direct Fallback trong `check_android_vpn` (`automation_core/preflight.py`)
- Khi runner (`tiktok_workflow` trong `run_post.py`) khởi động, nó kiểm tra preflight:
  ```python
  mapping_path = resolve_proxy_mapping_path()  # -> admin\PROXYgandienthoai.xlsx
  vpn_required = serial_is_mapped_in_workbook(...) # -> True
  require_android_vpn(adb, required=vpn_required, interface="auto")
  ```
- Trong `automation_core.preflight.check_android_vpn`:
  1. `global_proxy = _get_device_global_http_proxy(adb)` trả về `None` (do máy trả `:0`).
  2. Đoạn code kiểm tra egress IP rơi vào nhánh fallback:
     ```python
     if global_proxy:
         extracted_ip, ... = _probe_atx_curl_public_ip(adb, proxy=global_proxy, ...)
     else:
         # CẠM BẪY CHÍ MẠNG: Probe trực tiếp không truyền proxy!
         extracted_ip, ... = _probe_atx_curl_public_ip(adb, ...)
         if extracted_ip:
             proxy_ip = extracted_ip
             egress_ip_ok = True
     ```
  3. Vì mạng Wi-Fi `admin 2` (Ruijie AP) thông thẳng ra WAN FPT (không đi qua MikroTik), `atx-agent curl` probe trực tiếp bắt được IP WAN FPT: **`1.53.55.190`**.
  4. Code thấy `extracted_ip` là IPv4 public hợp lệ nên gán:
     `proxy_ip = '1.53.55.190'`, `egress_ip_ok = True`, `ip_verified = True`, `is_safe = True`!
  5. Preflight PASS $\to$ Mở TikTok chạy $\to$ **Toàn bộ tài khoản trên dàn máy S7 Admin dính chung IP FPT direct (`1.53.55.190`)**, gây nguy cơ chết nick hàng loạt!

## 3. Quy tắc bắt buộc khắc phục (Hard Invariant)
1. **Mapped Machine Phải Có Proxy:** Nếu một serial được xác định `required=True` (nằm trong `PROXYgandienthoai.xlsx`), preflight BẮT BUỘC kiểm tra thiết bị đã có `global_proxy` hợp lệ (`host:port`). Nếu `global_proxy is None` hoặc `:0`, BẮT BUỘC **FAIL-CLOSED LẬP TỨC**:
   `raise ConsumerPreflightError("Mapped device has no active global proxy configured (settings global http_proxy is empty/:0)")`
2. **CẤM Direct Probe Fallback khi Mapped:** Tuyệt đối không cho phép fallback sang direct probe khi máy thuộc diện bắt buộc dùng proxy.
3. **Phát hiện Direct IP Leak:** Nếu IP probe được trùng với IP WAN của host/farm (ví dụ `1.53.55.190`), lập tức chặn đứng với mã lỗi `DIRECT_IP_LEAK_BLOCKED`.
4. **Vận hành Farm Admin:** Phải luôn chạy `python D:\Taadaa\AI-Tools\scripts\set_proxy_farm_admin_adb.py` để gán proxy ADB cho dàn máy Admin trước khi chạy bất kỳ automation nào.
