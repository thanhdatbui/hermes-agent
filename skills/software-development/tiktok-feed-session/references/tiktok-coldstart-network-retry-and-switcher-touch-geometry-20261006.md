# TikTok Cold-Start Network Retry Overlay & Switcher Touch Geometry

## Bối cảnh sự cố (05/10 - 06/10/2026 trên M7 SM-G930F)
Ca upload video trước đó để lại banner lỗi mạng nháp, dẫn đến chuỗi dừng phiên `manual-needed:network` và `profile username still mismatched after switch` trong `run-feed-session.ps1`.

---

## 1. Cạm bẫy TikTok Cold-Start Network Retry Overlay (`dd9` / `ze3` / `message_tv`)

### Hiện tượng
- Wi-Fi và Proxy trên máy hoàn toàn sống (SignalStrength tốt, ping thông, curl qua proxy 20007 trả IP public và 204 OK).
- Khi TikTok vừa khởi động (Cold Start), do delay kết nối tạm thời, TikTok render overlay lỗi mạng:
  - Tiêu đề: `"Không có kết nối Internet. Hãy nhấn để thử lại."` (resource-id `com.ss.android.ugc.trill:id/ze3`)
  - Chú thích: `"Kết nối với internet và thử lại."` (resource-id `com.ss.android.ugc.trill:id/message_tv`)
  - Nút bấm: `"Thử lại"` (resource-id `com.ss.android.ugc.trill:id/dd9`, bounds `[144, 1329][936, 1485]`)

### Các điểm mấu chốt kỹ thuật đã vá
1. **Chặn `_swipe_recovery_on_stuck` trên màn hình lỗi mạng:**
   - Trong `_capture_step` và baseline stuck recovery, nếu `detected_screen in NETWORK_RETRY_SCREENS`, cấm tuyệt đối vuốt màn hình (vuốt không làm mới được trang mất mạng).
2. **Kích hoạt `allow_network_force_stop_recovery = True`:**
   - Hàm `_network_force_stop_recovery` (force-stop và relaunch TikTok sạch) bị chặn nếu cờ safety mặc định là `False`. Bắt buộc cho phép relaunch để nạp lại feed khi nút "Thử lại" chưa kịp giải phóng kết nối.
3. **Handler `_dismiss_network_error_retry` không tự quyết định thay flow chính:**
   - Handler chỉ chịu trách nhiệm tap trúng nút `dd9` (bounds `[144, 1329][936, 1485]`). Không tap mù giữa màn hình.
   - Việc hậu kiểm và calibrate/relaunch do flow chính trong `feed_swipe_smoke.py` điều phối qua `capture_calibration_attempt`.

---

## 2. Giao diện Switcher 8 Tài khoản & Tọa độ Chạm trên Samsung S7

### A. Roster 8 nick đẩy nút "Thêm tài khoản" ra ngoài tầm nhìn (off-screen)
- Chuẩn farm là 8 nick / máy. Danh sách 8 nick lấp đầy chiều cao màn hình.
- Nút `"Thêm tài khoản"` trượt xuống đáy ngoài màn hình.
- `_is_profile_account_switcher_xml` cũ bắt buộc cả `has_title and has_add_account` nên từ chối Switcher 8 nick.
- **Quy tắc mới:** Có tiêu đề `"Chuyển đổi tài khoản"` VÀ có ít nhất một dòng tài khoản hợp lệ (`account_rows`) là công nhận ngay Switcher hợp lệ.

### B. Nhiễu SystemUI Notifications
- Các thông báo từ Google Play ("Yêu cầu đăng nhập"), pin, đồng hồ lọt vào accessibility XML.
- Chỉ kiểm tra điều kiện loại trừ prose khi màn hình không có tiêu đề rõ ràng (titleless switcher).

### C. Tọa độ chạm dòng tài khoản toàn màn hình (Width = 1080px)
- Hàng tài khoản dạng `Button` trải dài `[0, 1140][1080, 1356]`.
- Tâm `x=540` rơi vào khoảng trống bên phải chữ tài khoản, bị Samsung nuốt sự kiện chạm và không kích hoạt đổi nick.
- **Khắc phục:** Giới hạn chiều rộng click target về `bounds[0] + 600` (đưa tâm tap về `x ≈ 300`), bảo đảm rơi trúng cụm text username và avatar.
