# MikroTik Direct Proxy vs Singbox Proxy Architecture (Farm Admin & Kibe)

## 1. Bản chất kiến trúc: Direct LAN Proxy vs Container Intermediary

| Đặc tính | Cụm Admin (Máy 201..280) | Cụm Kibe Legacy (Máy 01..80) |
|---|---|---|
| **Cổng proxy đích** | `192.168.110.2:10008..10035` | `192.168.110.2:20001..20080` |
| **Bản chất tầng mạng** | **Trực tiếp MikroTik LAN (3proxy)** | **Singbox Container (Trung gian)** |
| **Xác thực (Auth)** | Không auth / IP Whitelist LAN | Không auth trên port 200xx, Singbox inject auth ra upstream |
| **Hiệu năng & Độ trễ** | Tối ưu, 0 hop trung gian | Thêm 1 hop container xử lý và chuyển tiếp |
| **Nguy cơ lỗi** | Ít điểm gãy, thuần router OS | Lỗi DNS loop, firewall chặn cross-subnet container (172.17.x.x) |

## 2. Vì sao đi trực tiếp LAN MikroTik tối ưu hơn?
1. **Loại bỏ hoàn toàn Hop trung gian (Singbox):**
   - Không tốn tài nguyên CPU/RAM để Singbox giải mã, đệm và forward kết nối.
   - Giảm độ trễ gói tin (round-trip time), tránh connection timeout khi tải video/feed TikTok.
2. **Loại bỏ rủi ro Firewall chặn nhầm:**
   - Singbox chạy trong mạng container ảo (`172.17.0.0/16`). Nếu thiếu rule trong `FPT_LAN`, toàn bộ traffic bị drop âm thầm (`10054 Connection reset`).
   - Đi trực tiếp trên LAN `192.168.110.x` nằm sẵn trong subnet được phép kết nối ra router.
3. **Phân bổ đường truyền vật lý chuẩn xác 1:1:**
   - Mỗi cổng 1000x gắn cứng với một phiên quay số PPPoE riêng (`pppoe-out1`..`pppoe-out35`).

## 3. Quy tắc gán cho các máy Kibe dùng MikroTik (M33..M37, M71..M80)
- **🚨 BẪY LỆCH GIỮA TARGET ARCHITECTURE (TÀI LIỆU AI-TOOLS) & HIỆN TRẠNG ROUTER (2026-09-12):**
  + Tài liệu commit `533d2aaca` trong `AI-Tools` đề ra mục tiêu: 14 máy Kibe trỏ thẳng `192.168.110.2:10001..10007` để bỏ hop trung gian Sing-box.
  + **THỰC TẾ ROUTER CHƯA MỞ AUTH:** Các port `10001..10007` trên MikroTik do 3proxy quản lý hiện vẫn **bắt buộc xác thực tài khoản `admin@1:admin@1`**.
  + Vì Android `settings put global http_proxy` **KHÔNG hỗ trợ username/password**, nếu gán thẳng `192.168.110.2:1000X` lên S7, mọi request sẽ bị chặn với mã lỗi **`HTTP 407 Proxy Authentication Required`** -> Máy mất mạng 100%, TikTok báo *"Không có kết nối Internet / Đã xảy ra lỗi"*.
  + **ĐIỀU KIỆN TIÊN QUYẾT ĐỂ BỎ SING-BOX:** Phải sửa cấu hình 3proxy trên MikroTik sang `auth iponly` (whitelist toàn bộ dải LAN farm `192.168.110.0/24`) hoặc `auth none` cho các cổng 10001..10007.
  + **TRONG KHI CHỜ ĐỔI AUTH TRÊN ROUTER:** Toàn bộ 14 máy Kibe (M33..M37, M71..M80) **BẮT BUỘC vẫn phải dùng cổng Sing-box `20000+N`** (ví dụ M33 -> `20033`, M34 -> `20034`). Sing-box đóng vai trò inject `admin@1:admin@1` hộ Android để chuyển tiếp ra MikroTik. Tuyệt đối không gán 1000x trực tiếp vào S7 khi 3proxy chưa gỡ auth.

- **Mapping chuẩn 14 máy Kibe khi router đã gỡ auth:**
  - M33: 10001 (pppoe-out1)
  - M34: 10002 (pppoe-out2)
  - M35: 10003 (pppoe-out3)
  - M36: 10004 (pppoe-out4)
  - M37: 10005 (pppoe-out5)
  - M71: 10006 (pppoe-out6)
  - M72: 10001 (pppoe-out1)
  - M73: 10002 (pppoe-out2)
  - M74: 10003 (pppoe-out3)
  - M75: 10004 (pppoe-out4)
  - M77: 10005 (pppoe-out5)
  - M78: 10006 (pppoe-out6)
  - M79: 10007 (pppoe-out7)
  - M80: 10007 (pppoe-out7)
