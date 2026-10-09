# Samsung S7: Bẫy "No Internet AP", Cờ NET_CAPABILITY_VALIDATED & TikTok Chặn Mạng

## 1. Hiện Tượng & Nghịch Lý Thường Gặp
- **Trình duyệt (Browser) vào mạng bình thường:** Trên chính chiếc Samsung S7, mở Samsung Internet / Chrome truy cập `api.ipify.org` tải trang mượt mà, hiển thị đúng IP Public mới của proxy (`116.99.x.x` hoặc `171.231.x.x`).
- **Toybox NC / Curl trả về 200 OK:** Kiểm tra qua `toybox nc` tới gateway `192.168.110.2:<PORT>` trả về `HTTP/1.1 200 OK` hoặc `200 Connection established`.
- **NHƯNG App TikTok vẫn báo lỗi mất mạng:** Khi mở TikTok, màn hình lập tức hiện toast thông báo:
  > *"Không có kết nối Internet. Vui lòng kết nối với Internet và thử lại."*
  Kèm theo màn hình lỗi ở giữa: *"Đã xảy ra lỗi / Thử lại sau"* và nút *"Thử lại"* (`com.ss.android.ugc.trill:id/dcj`).

---

## 2. Nguyên Nhân Kỹ Thuật Cốt Lõi

### A. Sự khác biệt giữa Browser và Native App (TikTok)
1. **Trình duyệt:** Khi người dùng mở URL, Browser chỉ cần tạo socket HTTP/HTTPS qua proxy toàn cục (`settings get global http_proxy`). Proxy thông là web tải được.
2. **App TikTok:** Sử dụng engine Cronet / TTNet kết hợp với Android `ConnectivityManager`. TikTok đăng ký lắng nghe Network Callback và kiểm tra cờ năng lực mạng:
   ```java
   networkCapabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED)
   ```
   Nếu cờ này là `false`, TikTok tự động kết luận thiết bị không có kết nối Internet khả dụng, chủ động ngắt request feed và bắn toast lỗi ra UI ngay lập tức.

### B. Cơ chế "No Internet AP" của Samsung Experience (Android 8.0)
- Trên Samsung S7, dịch vụ `WifiConnectivityMonitor` và `NetworkMonitor` quản lý việc đánh giá chất lượng Wi-Fi.
- **Kịch bản sập bẫy:**
  1. Máy khởi động lại (soft-reboot) hoặc vừa kết nối Wi-Fi trong khi cổng proxy chưa sẵn sàng, hoặc lúc máy bị gán nhầm port PPPoE thô (HTTP 407).
  2. `WifiConnectivityMonitor` gửi request kiểm tra captive portal nhưng bị drop/timeout:
     `WifiConnectivityMonitor.CaptivePortalHandler: TIMEOUT_CAPTIVE_PORTAL reason: 3`
  3. `NetworkMonitor` lập tức phạt và ghim trạng thái:
     `NetworkMonitor/NetworkAgentInfo: No Internet AP - stay in current state`
  4. Trạng thái trong `dumpsys connectivity`:
     `lastValidated{false}`, `Score{20}` (thay vì `Score{60}` và `lastValidated{true}`).
- **Tính chất bẫy:** Do cơ chế quản lý Wi-Fi của Samsung, một khi đã bị đánh dấu `No Internet AP` trong RAM của tiến trình `system_server`, các lệnh tắt/bật Wi-Fi (`svc wifi disable/enable`) hoặc gán lại proxy KHÔNG XÓA ĐƯỢC cờ này. Thiết bị tiếp tục giữ cờ `UNVALIDATED`, khiến TikTok tiếp tục báo lỗi mất mạng vô thời hạn dù proxy đã thông suốt.

---

## 3. Quy Trình Xử Lý Dứt Điểm

1. **Bước 1: Xác thực chắc chắn Proxy & Egress IP đã sống 100%:**
   - Probe từ PC: `curl -s -m 5 -x http://192.168.110.2:<PORT> https://api.ipify.org` $\rightarrow$ 200 OK.
   - Probe từ thiết bị S7:
     ```bash
     adb -s <serial> shell 'printf "CONNECT www.tiktok.com:443 HTTP/1.1\r\nHost: www.tiktok.com:443\r\n\r\n" | toybox nc -w 4 -W 4 192.168.110.2 <PORT>'
     ```
2. **Bước 2: Giải phóng Stale Marker trong `device-readiness` (nếu có):**
   - Kiểm tra `~/.codex/device-readiness/<hash>.json`. Nếu kẹt `state: "proxy_pending"`, gọi:
     ```python
     from automation_core.readiness import mark_proxy_state
     mark_proxy_state(serial, "proxy_ready")
     ```
3. **Bước 3: Khởi động lại máy sạch (Clean Soft-Reboot):**
   - Chỉ có việc khởi động lại thiết bị mới xóa sạch cờ phạt `No Internet AP` trong `system_server` của Samsung.
   - Khi máy boot lên với proxy đã chuẩn bị sẵn và thông suốt, Android sẽ vượt qua khâu kiểm tra ban đầu, cấp cờ `&VALIDATED&`, đưa `Score` lên 60 và `lastValidated{true}`.
   - Khi đó mở TikTok sẽ load feed bình thường ngay lập tức.

---

## 4. Kỷ Luật Coordinator Khi Kiểm Tra Feed TikTok

- **CẤM KẾT LUẬN THÀNH CÔNG CHỈ DỰA VÀO TEXT XML NỀN:**
  - Trong cấu trúc UI của TikTok, các node text placeholder như *"Chào mừng bạn trở lại!"*, *"Hãy thích và bình luận để xem thêm nội dung bạn yêu thích"* vẫn tồn tại trong cây viewpager bên dưới ngay cả khi có lớp phủ lỗi đè lên trên.
  - **Dấu hiệu lỗi bắt buộc phải check:**
    - `com.ss.android.ugc.trill:id/tux_status_view` (Container thông báo lỗi).
    - Text: `Đã xảy ra lỗi`, `Thử lại sau`, `Thử lại` (`com.ss.android.ugc.trill:id/dcj`).
    - Toast / Overlay: `Không có kết nối Internet`.
  - **Bắt buộc đối chiếu Screencap thực tế** trước khi báo cáo cho user.
