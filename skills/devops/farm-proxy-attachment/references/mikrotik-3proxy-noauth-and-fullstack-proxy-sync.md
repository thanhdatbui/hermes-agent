# Postmortem & Architecture: 3proxy No-Auth Evolution, Direct IP Fallback Trap & Full-Stack Proxy Desync (2026-10-08)

## 1. Sự Cố & Hiện Trường Gốc
- **Hiện tượng:** Cụm MikroTik Admin (`10008..10035`) bị mất mạng/rớt PPPoE tạm thời. Tuy nhiên, script nuôi acc (`tiktok_workflow` / `multi_machine_feed_session.py`) trên máy Admin vẫn tiếp tục chạy và lướt TikTok ầm ầm.
- **Nguyên nhân gốc rễ (Root Cause):**
  1. *Lỗi cấu hình trên máy S7:* Toàn bộ dàn máy S7 Admin (201..280) bị tuột proxy về `:0` (Direct Wi-Fi) do trước đây 3proxy đặt mật khẩu `admin@1:admin@1`, trong khi Android OS qua ADB `settings put global http_proxy` không hỗ trợ user/pass, dẫn đến lỗi `HTTP 407 Proxy Authentication Required`.
  2. *Cạm bẫy Fallback trong Preflight (`automation_core/preflight.py`):* Khi thấy `global_proxy is None` (`:0`), hàm `check_android_vpn` ngộ nhận máy đang chạy ở chế độ "Router Transparent Proxy", tự động chuyển sang probe bằng `atx-agent curl` thẳng ra Wi-Fi không proxy. Wi-Fi Ruijie AP bắt trúng IP mạng nhà FPT `1.53.55.190`, preflight cấp cờ `is_safe = True` cho chạy $\rightarrow$ **Lộ Direct IP toàn bộ dàn nick**.

## 2. Giải Pháp Đột Phá: Bỏ Mật Khẩu 3proxy Container MikroTik
- **Quyết định kiến trúc của User:** RouterOS đã có sẵn 2 tầng tường lửa:
  + `ALLOW_FPT_LAN_PROXY_PORTS` (*15): Chỉ cho phép subnet nội bộ `FPT_LAN` (`192.168.110.0/24`, `192.168.10.0/24`, `172.17.0.0/16`) kết nối vào dải port proxy `10001..10035`.
  + `DROP_EXTERNAL_PROXY_PORTS` (*13): Khóa chặt tuyệt đối từ phía WAN.
  $\rightarrow$ **Việc đặt mật khẩu trên 3proxy là thừa thãi**, chỉ gây lỗi cho Android OS và làm phức tạp hóa hệ thống.
- **Thực thi trên MikroTik Soft Router:**
  ```bash
  # Cập nhật biến môi trường container 3proxy về rỗng
  PATCH /container/envs/*3 {"value": ""}  # HTTP_USER
  PATCH /container/envs/*4 {"value": ""}  # HTTP_PASS
  # Restart container 3proxy (*3)
  POST /container/stop {".id": "*3"}
  POST /container/start {".id": "*3"}
  ```
  $\rightarrow$ Toàn bộ 35 cổng PPPoE `10001..10035` chuyển sang chạy Direct HTTP không cần mật khẩu.

## 3. Quy Trình Đồng Bộ Toàn Bộ Hạ Tầng (Full-Stack Sync)
Khi bỏ mật khẩu MikroTik, **BẮT BUỘC ĐỒNG BỘ ĐỒNG LOẠT TẤT CẢ CÁC TẦNG**:
1. **58 Máy S7 Admin (ADB):** Chạy `scripts/set_proxy_farm_admin_adb.py` gán thẳng `192.168.110.2:10008..10035` lên toàn bộ máy online.
2. **File Excel Mapping:**
   - `D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx`: Sửa 16 dòng máy dùng MikroTik bỏ đuôi `:admin@1:admin@1`.
   - `D:\OneDrive\TaadaaData\admin\PROXYgandienthoai.xlsx`: Sửa 80 dòng máy Admin bỏ đuôi `:admin@1:admin@1`.
3. **GPMLogin v3 (`http://127.0.0.1:19995`):**
   - Quét toàn bộ profile qua API `/api/v3/profiles?limit=500`.
   - Các profile có `raw_proxy` chứa `admin@1:admin@1` $\rightarrow$ gọi `/api/v3/profiles/update/<id>` bỏ user/pass.
4. **9Router (`http://127.0.0.1:20128`):**
   - Quét `/api/proxy-pools`, lọc các pool `mirotik1.taadaa.click:10001..10004`.
   - Gọi `PUT /api/proxy-pools/<id>` thay thế URL từ `http://admin%401:admin%401@...` thành `http://mirotik1.taadaa.click:1000x/`.
5. **OmniRoute (:20129):**
   - Database SQLite của OmniRoute nằm tại `C:\Users\Kibe\.omniroute\storage.sqlite` (lưu ý: `getDefaultDataDir` ưu tiên legacy dot dir `.omniroute` nếu tồn tại, không dùng `AppData/Roaming/omniroute`).
   - Cập nhật bảng `proxy_registry`: `UPDATE proxy_registry SET username = '', password = '' WHERE host LIKE '%mirotik%';`
   - Cập nhật connection `OpenCode Free Pool` trong `provider_connections`: xóa sạch `username`/`password` trong JSON `provider_specific_data.accountProxies`.

## 4. Chốt Chặn Fail-Closed Triệt Để Trong Code Preflight
- **Vá tại `python_runner/core/vpn_preflight.py` và `Tiktok-video/scripts/tiktok_workflow/run_post.py`:**
  ```python
  # Kiểm tra bắt buộc: Máy có trong bảng mapping workbook thì settings global http_proxy KHÔNG ĐƯỢC PHÉP là :0 hoặc None
  if vpn_required:
      p_out = adb.shell(["settings", "get", "global", "http_proxy"], timeout=3.0, check=False)
      p_val = str(getattr(p_out, "stdout", "") or "").strip()
      if not p_val or p_val in ("null", ":0", "none"):
          raise ConsumerPreflightError(
              f"required Android VPN/proxy is not set on device: settings global http_proxy is missing or :0 for {device_id}"
          )
  ```
- **Chaos Test (Canary M252):**
  - Xóa proxy máy về `:0` $\rightarrow$ Preflight ném exception chặn đứng 100%.
  - Trỏ proxy vào port chết `:19999` $\rightarrow$ Probe socket/egress timeout chặn đứng 100%.
  - Trỏ proxy sống `:10025` $\rightarrow$ Egress IP PPPoE `116.110.5.226` pass và cho phép chạy.
