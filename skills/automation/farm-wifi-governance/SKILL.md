---
name: farm-wifi-governance
description: "Quy hoạch Wi-Fi Aruba farm, cấm gán SSID ngoài farm."
---

# Quy Hoạch Cố Định Wi-Fi Aruba & Cấm Gán Wi-Fi Ngoài Farm

## 1. QUY HOẠCH CỨNG 40 MÁY/AP (BẤT KHẢ XÂM PHẠM)
Hạ tầng Farm quy hoạch cố định 40 máy trên mỗi Access Point Aruba:
- **Máy 01 – 40**: CỐ ĐỊNH AP Aruba `.253` (SSID: `kibe 1`, Mật khẩu: `23102025`).
- **Máy 41 – 80**: CỐ ĐỊNH AP Aruba `.252` (SSID: `kibe 2`, Mật khẩu: `19051995`).
- **Máy 201 – 240**: CỐ ĐỊNH AP Aruba `.251` (SSID: `admin 1`, Mật khẩu: `19051995`).
- **Máy 241 – 280**: CỐ ĐỊNH AP Aruba `.250` (SSID: `admin 2`, Mật khẩu: `19051995`).

## 2. CẤM GÁN WI-FI NGOÀI FARM & CẤM FALLBACK BẬY
- **CẤM TUYỆT ĐỐI**: Cho máy nhảy sang bất kỳ SSID cá nhân/vãng lai ngoài farm (`Dat`, `Dat-1`, `BOX 2`...).
- **HẬU QUẢ**:
  1. Máy bị cấp IP dải `192.168.10.x` (thay vì dải chuẩn Farm `192.168.110.x`).
  2. Gãy kết nối tới Singbox / 3proxy trên MikroTik (`192.168.110.2:200xx`), gây lỗi proxy toàn hàng loạt.
  3. Rủi ro lộ IP direct FPT ra ngoài.
- **CẤM CODE FALLBACK**: Tuyệt đối không viết logic tự động thử kết nối sang SSID ngoài farm khi mất mạng.

## 3. CẤM TỰ Ý DỒN TẢI SANG AP KHÁC
- CẤM tự ý đề xuất hoặc dồn máy từ cụm này sang AP cụm khác (như M1–M40 sang `kibe 2`).
- Mỗi con AP Aruba chỉ chịu tải tối ưu tối đa ~40 máy. Dồn máy sẽ gây tràn bảng MAC, tăng tỉ lệ drop frame và nghẽn toàn bộ luồng mạng.

## 4. QUY TRÌNH CỨU HỘ WI-FI 2 CẤP CHUẨN
Khi máy mất mạng Wi-Fi:
- **Cấp 1 (Radio Toggle)**:
  ```bash
  adb -s <serial> shell svc wifi disable
  sleep 1
  adb -s <serial> shell svc wifi enable
  sleep 3
  ```
- **Cấp 2 (Bẻ khóa blocklist bằng adb-join-wifi)**:
  Nếu máy dính cờ `ASSOCIATION_REJECTION` từ AP, ép re-join đúng SSID quy hoạch:
  ```bash
  adb -s <serial> shell 'am force-stop com.steinwurf.adbjoinwifi && am start -n com.steinwurf.adbjoinwifi/.MainActivity --es ssid "<SSID>" --es password_type WPA --es password "<PASSWORD>"'
  sleep 4
  adb -s <serial> shell input keyevent 3
  ```
  *(Lưu ý: BẮT BUỘC dùng `--es ssid "<SSID>"` để tránh việc Android shell cắt mất ký tự số sau khoảng trắng).*
- **Xử lý khi cả 2 cấp thất bại**:
  BẮT BUỘC giữ nguyên hiện trường máy lỗi và báo lỗi watchdog để kỹ thuật kiểm tra AP/phần cứng. **TUYỆT ĐỐI CẤM gán bừa mạng khác để chữa cháy**.
