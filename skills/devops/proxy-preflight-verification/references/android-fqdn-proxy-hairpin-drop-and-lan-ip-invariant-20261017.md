# Bẫy Gán FQDN/Domain Vào Android HTTP_PROXY & Cơ Chế Hairpin NAT Firewall Drop (2026-10-17 Invariant)

**Ngày ghi nhận:** 17/10/2026  
**Ngữ cảnh áp dụng:** Áp dụng cho toàn bộ 160 máy Phone Farm (80 máy Kibe M1–80 và 80 máy Admin M201–280), các script gán proxy ADB (`set_proxy_farm_adb.py`, `set_proxy_farm_admin_adb.py`), và mapping proxy trong Excel (`PROXYgandienthoai.xlsx`).

---

## 1. Bản Chất Sự Cố (Root Cause & The FQDN Trap)

### Hiện tượng:
- Điện thoại Android trên thanh Status Bar xuất hiện icon Wi-Fi kèm **dấu chấm than** (`!`).
- Node hệ thống trong `popup_before.xml`:
  `<node index="8" resource-id="com.android.systemui:id/wifi_combo" content-desc="Tín hiệu Wi-Fi ba vạch.,Không có Internet." bounds="[734,14][781,56]" />`
- Mặc dù trên router MikroTik:
  * Interface PPPoE báo uptime liên tục > 7 ngày (`1w 11h 30m`), không hề rớt mạng nhà mạng.
  * Test từ PC host tới cổng proxy MikroTik (`192.168.110.2:1000x`) phản hồi `HTTP 200 OK` tức thời trong 0.1s.

### Tại sao lại xảy ra nghịch lý này?
1. **Bẫy phân giải tên miền (DNS Resolution Mismatch):**
   - Trên máy tính host (PC): Tên miền `mirotik1.taadaa.click` hoặc được cấu hình trong file `hosts` hoặc phân giải nội bộ qua router về thẳng IP LAN `192.168.110.2`. Do đó, kiểm tra từ PC luôn luôn thành công.
   - Trên điện thoại Android: Android gửi truy vấn DNS ra DNS resolver ngoài (như `8.8.8.8` hoặc DNS nhà mạng). Domain `mirotik1.taadaa.click` được phân giải ra **IP Public WAN Viettel** (`116.99.168.85`).
2. **Cơ chế chặn tường lửa MikroTik (Hairpin NAT & Firewall Drop):**
   - Khi điện thoại Android (`192.168.110.222`) gửi gói tin tới IP Public WAN `116.99.168.85:10002`:
     * Router MikroTik có rule bảo vệ:
       `chain=forward dst-port=10001-10035 action=drop comment=DROP_EXTERNAL_PROXY_PORTS`
     * Rule này chặn toàn bộ các gói tin nhắm vào cổng proxy nếu nguồn hoặc đích không khớp whitelist LAN hoặc đi qua interface WAN.
     * Hơn nữa, Hairpin NAT không được bật cho dải cổng proxy nhằm tránh loopback quá tải CPU router.
   - **Kết quả:** Toàn bộ kết nối TCP từ điện thoại tới proxy bị **DROP HOÀN TOÀN** (`Connection Refused` hoặc `Timeout`).
3. **Ảnh hưởng tới ứng dụng (TikTok & Captive Portal):**
   - Android gửi gói thăm dò captive portal `generate_204` thất bại -> Gắn cờ `"Không có Internet"`.
   - TikTok khi tap đổi tài khoản (Account Switcher) cần gửi API lên server lấy session token. Do mất mạng, TikTok hiển thị vòng xoay `tux_loading_hud`, sau đó hủy bỏ thao tác chuyển đổi tài khoản và giữ nguyên nick cũ.
   - Script runner bước sang bước verify profile thấy nick chưa đổi -> ném lỗi `ACCOUNT_VERIFY_MISMATCH`. Watchdog bắt lỗi và kích hoạt cảnh báo sai: `P0 CẢNH BÁO MẤT PHIÊN / VĂNG ACCOUNT`.

---

## 2. Quy Tắc Bất Biến & Chốt Chặn Toàn Farm (Hard Invariants)

1. **CẤM TUYỆT ĐỐI GÁN PROXY DẠNG DOMAIN/FQDN CHO ANDROID:**
   - CẤM TUYỆT ĐỐI dùng `adb shell settings put global http_proxy` với hostname/domain (như `mirotik1.taadaa.click`, `test.taadaa.click`...).
   - **BẮT BUỘC LUÔN LUÔN DÙNG IP NỘI BỘ LAN:** `192.168.110.2:<port>`.
2. **LUÔN TẮT CAPTIVE PORTAL KÈM THEO:**
   - Mọi script gán proxy bắt buộc phải thực thi 2 lệnh đi kèm:
     ```bash
     adb -s <serial> shell settings put global captive_portal_mode 0
     adb -s <serial> shell settings put global captive_portal_detection_enabled 0
     ```
   - Điều này ngăn Android tự động ngắt kết nối Wi-Fi hoặc hiện dấu chấm than khi mạng có độ trễ.
3. **QUY HOẠCH CỔNG GÁN CHUẨN:**
   - **Farm Kibe (Máy 1–80):**
     * Dải cổng Sing-box nội bộ: `192.168.110.2:20001..20080` (tương ứng `20000 + M`).
   - **Farm Admin (Máy 201–280):**
     * Dải cổng MikroTik PPPoE trực tiếp: `192.168.110.2:10008..10035` hoặc Sing-box `192.168.110.2:20201..20280`.
4. **CHUẨN HÓA DỮ LIỆU EXCEL (SOURCE OF TRUTH):**
   - File `D:/OneDrive/TaadaaData/kibe/PROXYgandienthoai.xlsx` và `admin/PROXYgandienthoai.xlsx` tại Cột C bắt buộc lưu định dạng IP LAN `192.168.110.2:<port>`.
   - CẤM TUYỆT ĐỐI lưu domain `mirotik1.taadaa.click` trong file Excel để tránh việc script tự động đọc và gán nhầm domain vào máy.

---

## 3. Vá Mã Nguồn Runner (Code Hardening)

1. **Kiểm tra trạng thái mạng trước khi mở Switcher (`feed_swipe_smoke.py`):**
   - Trước khi tap chọn account, kiểm tra nếu UI XML có chứa chuỗi `"Không có Internet"`:
     Lập tức fail-fast với lý do `manual-needed:network-offline: Wi-Fi has no internet connection (wifi_combo status)`.
   - Tuyệt đối không cố tap chọn nick khi mạng đang mất để tránh bị kẹt modal loading.
2. **Chờ biến mất loading spinner (`tux_loading_hud`):**
   - Sau khi tap chọn nick và điều hướng về Profile, kiểm tra vòng lặp tối đa 5 giây:
     Nếu màn hình vẫn còn `tux_loading_hud`, ngủ 1.0s chờ TikTok nạp xong session mới từ server rồi mới đọc Profile Identity.
3. **Timeout Guard cho script gán Proxy ADB (`set_proxy_farm_adb.py`):**
   - Đặt `timeout=8s` cho các lệnh ADB `settings put global http_proxy` và `timeout=5s` cho captive portal.
   - Ngăn chặn tình trạng 1 máy bị lỏng cáp / USB treo làm đơ toàn bộ tiến trình gán proxy của fleet.
