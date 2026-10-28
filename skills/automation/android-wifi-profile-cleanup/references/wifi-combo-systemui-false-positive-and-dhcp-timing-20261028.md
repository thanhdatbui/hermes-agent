# SystemUI wifi_combo False Positive & DHCP Wake-Up Window Triage (2026-10-28)

## 1. Hiện Tượng & Triệu Chứng (Farm Alert)
Watchdog báo cáo hàng loạt máy farm Admin (ví dụ M216, M229, M268, M277) bị:
`- Mất kết nối Wi-Fi (AP) (4): M216, M229, M268, M277`

Tuy nhiên, khi đối soát thời gian thực qua `inspect_machine.py` hoặc ca chạy kế tiếp (`row-0-080046`), tất cả các máy đều có IP chuẩn `192.168.110.x`, Proxy thông, và chạy hoàn thành `status: success` 100% mà không hề cần reboot hay chỉnh sửa phần cứng.

---

## 2. Phân Tích 2 Nhánh Nguyên Nhân Gốc (Root Cause)

### Nhánh 1: Cửa sổ DHCP Lease khi thức dậy (M229, M268)
- **Lỗi ghi nhận:** `stop_reason: required router proxy is unreachable ... dumpsys connectivity: Wi-Fi not connected`
- **Cơ chế:** Máy ở trạng thái ngủ sâu (`Sleep/Dozing`) qua đêm. Khi bắt đầu ca sáng (06:00:49), 80 máy cùng thức dậy kết nối lại AP Aruba.
- **Lệch pha thời gian:** Chip Broadcom trên Samsung S7 (Android 8) cần **5–7 giây** để hoàn tất bắt tay WPA2 và xin lease DHCP. Nhưng `vpn_preflight.py` thăm dò quá sớm (`time.sleep(2.0)`), kết luận sai rằng Wi-Fi không kết nối và kích hoạt ngắt ca để bảo vệ nick.

### Nhánh 2: Bẫy SystemUI `wifi_combo` Status Bar (M216, M277)
- **Lỗi ghi nhận:** `manual-needed:network-offline: Wi-Fi has no internet connection (wifi_combo status)`
- **Cơ chế:**
  1. Máy đã kết nối Wi-Fi, mở TikTok và vào thành công màn hình Switcher danh sách tài khoản.
  2. Trong `feed_swipe_smoke.py`, hàm `_switcher_offline_reason(popup_xml)` quét chuỗi `"khong co internet"` trên toàn bộ XML màn hình.
  3. Do máy chạy qua HTTP Proxy (`settings put global http_proxy 192.168.110.2:100xx`), gói kiểm tra captive portal của Android OS (`generate_204`) bị trễ hoặc chặn, khiến icon Wi-Fi trên đỉnh màn hình (`com.android.systemui:id/wifi_combo`) mang thuộc tính `content-desc="Tín hiệu Wi-Fi đủ.,Không có Internet."`.
  4. Code runner quét trúng node của `com.android.systemui` -> nhầm lẫn rằng TikTok không có mạng -> abort chuyển nick.
  5. Trong `formatters.py`, watchdog thấy chuỗi `wifi_combo` / `network-offline` nên gom vào nhóm **"Mất kết nối Wi-Fi (AP)"**, tạo ảo giác AP rớt mạng.

---

## 3. Bài Học & Giải Pháp Kỹ Thuật

1. **Preflight DHCP Timing Window:**
   - Sau khi bật Wi-Fi hoặc đánh thức thiết bị, thời gian lắng đọng tối thiểu phải đạt **6 – 8 giây** trước khi kiểm tra `dumpsys connectivity`.

2. **Scoped Offline Detection trong XML:**
   - Khi kiểm tra cờ offline hoặc pop-up cảnh báo mất mạng, BẮT BUỘC chỉ tìm trong các node có `package="com.ss.android.ugc.trill"`.
   - Tuyệt đối loại trừ các node thuộc `package="com.android.systemui"` để không bị đánh lừa bởi thanh trạng thái của hệ điều hành.

3. **Kỷ luật Triage Điều Phối (Coordinator Invariant):**
   - Khi nhận Farm Alert "Mất kết nối Wi-Fi", không phỏng đoán theo nhãn watchdog.
   - Trích xuất O(1) `inspect_machine.py` để xác định trạng thái thực tế.
   - So sánh manifest của run liền kề để nhận diện ảo giác phần cứng do bão handshake hoặc false-positive cảnh báo.
