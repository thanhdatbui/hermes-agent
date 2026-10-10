# Lệch Cấu Hình Dải Cổng Farm Admin M201-M280 Vượt Ngưỡng 40 Port MikroTik (2026-10-10)

## 1. Hiện Tượng Thực Tế
Trong ca nuôi lướt feed batch quy mô 80 máy trên Farm Admin (M201–M280), hệ thống ghi nhận tỷ lệ lỗi vượt ngưỡng kép (57.5% thất bại: 46/80 máy):
- 24 máy fail-closed với đúng 1 signature:
  `proxy-vpn:required Android VPN/proxy is unreachable: proxy server port is closed/refused for <serial>; skipping recovery wait to unblock other machines immediately`
- Danh sách 24 máy lỗi: `M241, M242, M243, M244, M245, M246, M247, M248, M249, M250, M253, M254, M256, M257, M258, M259, M260, M261, M262, M264, M271, M272, M273, M280`.
- Đặc điểm nhận diện: **100% các máy lỗi đều có số máy >= 241**. Toàn bộ máy từ M201 đến M240 đều pass kiểm tra socket proxy.

## 2. Nguyên Nhân Gốc (Root Cause)
1. **Lệch công thức gán trên thiết bị vs Thực tế cổng MikroTik:**
   - Trên thiết bị Android, cài đặt `settings get global http_proxy` bị gán nhầm theo công thức 1 máy / 1 port: `port = 10000 + M - 200`:
     * M201 -> `192.168.110.2:10001`
     * M240 -> `192.168.110.2:10040`
     * M241 -> `192.168.110.2:10041`
     * M280 -> `192.168.110.2:10080`
   - Hạ tầng MikroTik x86 (`192.168.110.2`) chỉ cấu hình tối đa **40 đường PPPoE (cổng 10001..10040)**.
   - Các cổng từ `10041` đến `10080` **KHÔNG TỒN TẠI** trên MikroTik, trả về `Connection Refused` / `10035`.
2. **Cơ chế Fast Fail-Closed hoạt động chính xác:**
   - Preflight `_proxy_server_live` ưu tiên đọc proxy đang active trên thiết bị (`settings get global http_proxy`).
   - Với M201..M240: probe socket cổng `10001..10040` thành công (`connect_ex == 0`).
   - Với M241..M280: probe socket cổng `10041..10080` bị từ chối (`connect_ex != 0`), kích hoạt fast fail-closed `<= 1.5s` để chống rò rỉ IP FPT trực tiếp.

## 3. Quy Hoạch Chuẩn & Quy Trình Khôi Phục (Recovery)
1. **SSOT Mapping:**
   - File mapping chuẩn `D:\OneDrive\TaadaaData\admin\PROXYgandienthoai.xlsx` đã quy hoạch ghép cặp 2–3 máy / port cho toàn bộ 80 máy Admin vào dải cổng MikroTik `10008..10035`.
2. **Kiểm chứng Canary trên 1 máy đại diện (M241):**
   - Đọc mapping M241 -> port `10021`.
   - Gán `settings put global http_proxy 192.168.110.2:10021`.
   - Đối soát socket: `connect_ex(('192.168.110.2', 10021)) == 0`.
   - Đối soát egress IP qua atx-agent curl:
     `export http_proxy=http://192.168.110.2:10021; export HTTP_PROXY=http://192.168.110.2:10021; /data/local/tmp/atx-agent curl --timeout=5s http://icanhazip.com`
     -> Trả về đúng IP WAN Viettel PPPoE (ví dụ: `171.231.188.208`), exit code 0.
3. **Đồng bộ hàng loạt an toàn trên Farm Admin:**
   - Chạy script gán chuẩn hóa qua SSH tới PC Admin:
     `ssh admin-farm "powershell -Command \"python -u D:/Taadaa/AI-Tools/scripts/set_proxy_farm_admin_adb.py\""`
   - Script tự động đọc `D:\OneDrive\TaadaaData\admin\PROXYgandienthoai.xlsx` và cập nhật cổng `10008..10035` cho toàn bộ máy online, đồng thời tắt captive portal.
