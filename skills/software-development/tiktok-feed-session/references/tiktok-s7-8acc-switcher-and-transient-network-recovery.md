# TikTok S7 8-Account Switcher & Transient Cold-Start Network Recovery (2026-10-05)

## 1. Samsung S7 8-Account Full Roster Switcher Trap

### Hiện tượng
- Trên các máy Samsung S7 cấu hình chuẩn 8 tài khoản (full roster farm), khi mở Account Switcher từ Profile, danh sách 8 tài khoản lấp đầy toàn bộ chiều cao màn hình.
- Nút **"Thêm tài khoản"** (`_is_add_account_option_text`) bị cuộn ra khỏi vùng nhìn thấy (`off-screen`, y > 1920).
- Hàm nhận diện Switcher cũ bắt buộc đồng thời `has_title and has_add_account` ➔ Coi màn hình Switcher 8 nick là màn hình lạ, dừng phiên báo `manual-needed: account switcher requires manual review`.

### Giải pháp
- Cho phép nhận diện Switcher khi:
  ```python
  has_title = bool(values.intersection(_ACCOUNT_SWITCHER_TITLES))
  has_add_account = any(_is_add_account_option_text(value) for value in values)
  account_rows = {value.lstrip("@") for value in values if _looks_like_account(value)}
  if has_title and (has_add_account or bool(account_rows)):
      return True
  ```

---

## 2. Bẫy Tọa Độ Chạm Dòng Tài Khoản (Full-Width Button Tap Trap)

### Hiện tượng
- Trong Account Switcher trên Samsung S7, mỗi dòng tài khoản là một `android.widget.Button` có bounds trải dài toàn bộ chiều ngang màn hình `[0, y1][1080, y2]`.
- Username thực tế chỉ chiếm nửa bên trái (ví dụ `x=252..521`).
- Khi tính tọa độ tâm `center_x = (0 + 1080) // 2 = 540`, điểm chạm rơi vào khoảng trống màu trắng bên phải tên tài khoản. Trên giao diện Samsung TouchWiz / OneUI cũ, sự kiện tap vào khoảng trống bị nuốt và TikTok **không thực hiện chuyển tài khoản**.
- Hệ quả: Switcher đóng lại nhưng tài khoản active trên Profile vẫn giữ nguyên nick cũ ➔ Script báo `profile username still mismatched after switch`.

### Giải pháp
- Giới hạn chiều rộng tối đa của các hàng tài khoản rộng >= 600px về dải `0..700px`:
  ```python
  if best_bounds[2] - best_bounds[0] >= 600:
      best_bounds = (best_bounds[0], best_bounds[1], min(best_bounds[2], 700), best_bounds[3])
  ```
- Tọa độ tâm tap dịch về `x ~ 350`, rơi chính xác vào trọng tâm cụm chữ tên tài khoản, đảm bảo 100% kích hoạt chuyển nick.

---

## 3. Banner Lỗi Tải Video Che Khuất Profile Header

### Hiện tượng
- Khi ca upload trước đó bị lỗi mạng, TikTok lưu video vào bản nháp và hiển thị banner đỏ trên đỉnh trang Profile: *"Không thể tải video lên. Đã lưu bản nháp. Chạm để thử lại"* (resource-id `tv_tips`, nút đóng `ea5` tại `[960,138][1008,186]`).
- Banner này che phủ toàn bộ header (y=102..357), làm mất thanh hiển thị username / display-name anchor.
- Từ khóa tab thư mục nháp *"Bản nháp: 1"* bị bộ phân tích nhận diện nhầm thành display name người dùng.

### Giải pháp
- Tự động đóng banner qua nút `ea5` trước khi phân tích Profile.
- Bổ sung tiền tố `"bản nháp"`, `"draft"` vào `profile_placeholder_texts` trong `is_profile_placeholder` để không bao giờ nhận vơ tab nháp làm tên tài khoản.

---

## 4. Xử Lý Transient Network Error Lúc Khởi Động (Cold-Start Network Overlay)

### Hiện tượng
- Khi TikTok vừa cold-start, do delay mạng/proxy ban đầu, app hiển thị màn hình lỗi: *"Không có kết nối Internet. Hãy nhấn để thử lại."* kèm nút **"Thử lại"** (`com.ss.android.ugc.trill:id/dd9`).
- **Sai lầm 1:** Chạy `_swipe_recovery_on_stuck` (vuốt feed lên). Trên màn hình lỗi mạng, vuốt feed hoàn toàn vô dụng, dẫn đến kẹt 2 swipes rồi fail.
- **Sai lầm 2:** Tap nút "Thử lại" nhưng không hậu kiểm UI dump xem lỗi đã biến mất chưa.
- **Sai lầm 3:** Cờ `allow_network_force_stop_recovery` bị mặc định là `False`, khiến script không cho phép force-stop relaunch app sạch khi gặp lỗi mạng tạm thời lúc khởi động.

### Giải pháp
1. Chặn `_swipe_recovery_on_stuck` kích hoạt khi `detected_screen in NETWORK_RETRY_SCREENS`.
2. Tap nút `dd9` / `retry` / `reload` có bounds cụ thể, cấm tap mù giữa màn hình.
3. Hậu kiểm bằng `_safe_capture_hierarchy()`. Nếu còn marker `dd9`/`ze3`/`message_tv` ➔ trả `network_retry_postcondition_failed`.
4. Mặc định `allow_network_force_stop_recovery = True` để hệ thống tự động force-stop và relaunch app nạp lại phiên mới khi nút thử lại chưa kịp nhả.
