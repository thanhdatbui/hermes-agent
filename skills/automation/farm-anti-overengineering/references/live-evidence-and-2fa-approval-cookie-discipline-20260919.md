# Kỷ Luật Nghiệm Thu Ảnh Hiện Trường Thật & Tự Động Phê Duyệt 2FA, Xử Lý Cookie Popup (19/09/2026)

## 1. Kỷ Luật Nghiệm Thu Bằng Chứng Hình Ảnh (Media Evidence Discipline)
- **CẤM gửi ảnh màn hình HOME**: Khi nghiệm thu tác vụ can thiệp thiết bị (Canary/Recovery/Batch), TUYỆT ĐỐI KHÔNG chụp ảnh sau khi app đã bị đóng hoặc đã bấm phím HOME. Phải chụp ảnh lúc app/trình duyệt đang ở đúng màn hình hiện trường cần chứng minh (màn hình lỗi, màn hình OTP, màn hình xác thực, giao diện sau khi click).
- **Tránh chụp màn hình đen (Screen Off / Sleep)**: Trước khi screencap qua ADB, bắt buộc gửi `input keyevent 224` (WAKEUP) để đảm bảo màn hình đang bật sáng (Display Power: ON), tránh file ảnh đen kịt RGB (0,0,0).
- **Khóa góc xoay màn hình (Orientation Lock)**: Tránh trường hợp thiết bị tự xoay ngang (`mCurrentRotation=1`) làm lệch toàn bộ tọa độ tap. Phải đảm bảo `user_rotation = 0` và `accelerometer_rotation = 0` (Portrait 1080x1920).

## 2. Xử Lý Tự Động Phê Duyệt 2FA Authenticator (Google 2SV Popup)
- **Hiện tượng**: Sau khi submit mã TOTP 6 chữ số để bật Google Authenticator trên web, Google hiện popup bảo mật: *"Phê duyệt trình xác thực này? Để đẩy nhanh quá trình này, bạn có thể phê duyệt trình xác thực mới... [Xóa] [Phê duyệt]"*.
- **Tính chất**: Popup này **CHỈ XUẤT HIỆN 1 LẦN DUY NHẤT** ngay thời điểm vừa add key xong. Nếu đóng tab hoặc bỏ qua, Google sẽ đưa trình xác thực vào danh sách chờ ngâm bảo mật và không hiện lại nút phê duyệt nữa.
- **Giải pháp**:
  ```python
  # Sau khi click verify OTP thành công:
  try:
      approve_btn = page.locator('button:visible, [role="button"]:visible').filter(has_text=re.compile(r"phê duyệt|approve", re.I)).first
      if approve_btn.is_visible():
          approve_btn.click(force=True)
          time.sleep(3)
  except Exception as e_appr:
      pass
  ```

## 3. Vượt Cookie Banner Khi Chrome Android Giấu DOM Vào WebView
- **Hiện tượng**: Chrome trên Android render trang web (như `chatgpt.com`) dưới dạng một `FrameLayout` "Lượt xem trên web" nguyên khối. `uiautomator dump` không trích xuất được text con bên trong DOM HTML.
- **Hậu quả**: Các hàm dò text XML (`find_node_in_xml`) bị mù hoàn toàn, script chờ timeout lãng phí thời gian.
- **Giải pháp Fallback Tap Tọa Độ Chuẩn (Samsung S7 - 1080x1920)**:
  - Nút **`[Chấp nhận tất cả]` / `[Accept all]`**: Tọa độ `(540, 1780)`.
  - Ô input **`[Email address]`**: Tọa độ `(540, 1315)`.
  - Nút **`[Tiếp tục]` / `[Continue]`**: Tọa độ `(540, 1485)`.

## 4. Bộ Lọc 2FA Bắt Buộc Trước Khi Login GPMLogin Ca Tối
- **Invariant**: Tuyệt đối KHÔNG đưa tài khoản Gmail chưa có `2FA_Secret` vào luồng login tự động GPMLogin trên PC.
- **Lý do**: Môi trường trình duyệt PC lạ + IP mới sẽ khiến Google lập tức kích hoạt `hard_phone_checkpoint` (đòi SMS SĐT mới) đối với các tài khoản không có 2FA, làm cháy quota proxy và khóa nick.
- **Bộ lọc trong `post_evening_gpm_login_watchdog.py`**:
  ```python
  two_fa = str(r[4] or "").strip()
  if not two_fa or two_fa.upper() == "NONE":
      continue
  ```
