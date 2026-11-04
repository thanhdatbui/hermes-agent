# Báo Cáo & Bài Học Kỹ Thuật: Khắc Phục Lỗi Loopback Singbox 16 Máy Kibe & Chuẩn Hóa Cấu Hình Gộp (2026-11-04)

## 1. Hiện Tượng Farm Alert & Triệu Chứng Thực Tế
- **Cảnh báo:** `[BATCH ALERT: LỖI HỆ THỐNG] PHÁT HIỆN LỖI LAN RỘNG - 【FARM KIBE - MÁY 1-80】` trong quy trình nuôi acc / lướt feed (`tiktok-luot nuoi acc`).
- **Tỷ lệ lỗi:** 12 máy bị fail với cùng signature:
  `global proxy (<serial>) egress IP verification failed: ... context deadline exceeded (Client.Timeout exceeded while awaiting headers)`.
- **Danh sách máy bị ảnh hưởng:** `M33, M34, M36, M38, M71, M72, M73, M74, M75, M76, M77, M79`.
- **Kết quả đo kiểm Canary M33 ban đầu:** Kết nối proxy `192.168.110.2:20033` bị `TimeoutError: timed out`.

## 2. Nguyên Nhân Gốc Rễ (Root Cause: Bẫy Loopback Trong Singbox)
- **Bản chất nhóm 16 máy Kibe:** `M33–M38` và `M71–M80` là 16 máy Kibe được quy hoạch chạy qua các đường mạng MikroTik PPPoE (`10001..10007`) và proxy phụ trợ `khoalee` (`16002`).
- **Sai lệch dữ liệu Excel & Script gen:**
  - Trong file Excel `D:/OneDrive/TaadaaData/kibe/PROXYgandienthoai.xlsx`, cột proxy của các máy này bị điền nhầm thành chính IP:Port của Singbox inbound (`192.168.110.2:20033`, `192.168.110.2:20034`...).
  - Script `generate_singbox_config.py` đọc từ Excel này và tạo ra outbounds:
    ```json
    {"type": "http", "tag": "proxy_m33", "server": "192.168.110.2", "server_port": 20033}
    ```
  - **Hậu quả:** Khi điện thoại gửi request tới cổng 20033 của Singbox $\rightarrow$ Singbox lại mở socket kết nối vào chính cổng 20033 của chính nó (Self-Loopback).
  - **Log Container MikroTik (`/rest/log`):**
    `ERROR ... using outbound/http[proxy_m38]: dial tcp 192.168.110.2:20038: connect: cannot assign requested address`
    Hệ điều hành cạn socket và từ chối cấp phát $\rightarrow$ Runner preflight bị timeout $\rightarrow$ Kích hoạt Fail-Closed bảo vệ nick.

## 3. Quy Chuẩn Khắc Phục Triệt Để
1. **Khóa Cứng Mapping Trong Code Generator:**
   - Trong `D:/Taadaa/AI-Tools/scripts/generate_singbox_config.py`, bổ sung các hằng số:
     ```python
     MIROTIK_MACHINES = [33, 34, 35, 36, 37, 71, 72, 73, 74, 75, 77, 78, 79, 80]
     MIROTIK_SERVER = "mirotik1.taadaa.click"
     MIROTIK_PORT_START = 10001
     MIROTIK_PORT_END = 10007
     MIROTIK_USER = "admin@1"
     MIROTIK_PASS = "admin@1"

     KHOALEE_MACHINES = [38, 76]
     KHOALEE_SERVER = "khoalee.duckdns.org"
     KHOALEE_PORT = 16002
     KHOALEE_USER = "5ns08q"
     KHOALEE_PASS = "AmLmaMJ0"
     ```
   - Ánh xạ đan xen 14 máy qua 7 port MikroTik PPPoE (`10001-10007`), 2 máy `M38` và `M76` qua `khoalee:16002`.
2. **Sinh File Cấu Hình Gộp Minified:**
   - Chạy `generate_singbox_config.py --profile both` để tạo file cấu hình gộp 112 máy (80 Kibe + 32 Admin non/yếu).
   - Nén minified (`singbox_full_160_min.json`, ~27KB) để giảm thiểu payload.
3. **Nạp Cấu Hình Lên RouterOS Container:**
   - Dùng RouterOS REST API:
     `PATCH http://192.168.110.2:9090/rest/file/*8072575` với body `{"contents": "<minified_json>"}`.
   - Gửi tín hiệu Stop container `*6` $\rightarrow$ chờ 5s $\rightarrow$ Start container `*6`.
   - Xác nhận container quay lại trạng thái `status: running`.

## 4. Nghiệm Thu & Kiểm Chứng Thực Tế (Ground Truth)
- Cổng `20033` (M33 Canary): Trả về `171.231.180.189` (Line `pppoe-out1` MikroTik Đà Nẵng, HTTP 200 tức thời).
- Cả 12 máy lỗi trong Alert và 4 máy cùng cụm (`M35, M37, M78, M80`) đều LIVE 100%, trả về đúng IP Public độc lập:
  - `M33, M73`: `171.231.180.189`
  - `M34, M74`: `27.79.42.241`
  - `M35, M75`: `27.79.0.226`
  - `M36, M77`: `171.231.177.71`
  - `M37, M78`: `116.110.219.23`
  - `M38, M76`: `117.5.56.83` (KhoaLee)
  - `M71, M79`: `171.231.197.191`
  - `M72, M80`: `116.110.215.166`
