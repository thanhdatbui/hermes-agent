# Quy tắc Gửi ảnh Farm Alert Banner Đỏ & Xử lý Kẹt Màn hình Đăng ký TikTok (2026-08-24)

## 1. Quy tắc BẮT BUỘC: Gửi ảnh màn hình máy lỗi kèm Banner Đỏ
- **Yêu cầu của User**: Mọi ảnh chụp màn hình máy lỗi khi gửi cho user / báo cáo farm **BẮT BUỘC phải chèn banner đỏ ghi rõ số máy `[MAY X] - HH:MM:SS dd/mm`** ở đầu ảnh (theo chuẩn hàm `send_farm_machine_alert` của `automation_core.alerts`).
- **CẤM TUYỆT ĐỐI**: Gửi ảnh màn hình trơn không có số máy / không có banner.
- **Cách tạo ảnh banner đỏ nhanh bằng Python (Pillow)**:
  ```python
  import io, datetime
  from PIL import Image, ImageDraw, ImageFont

  proc = subprocess.run([adb_path, "-s", serial, "exec-out", "screencap", "-p"], capture_output=True)
  if proc.returncode == 0 and len(proc.stdout) > 1000:
      img = Image.open(io.BytesIO(proc.stdout)).convert("RGB")
      draw = ImageDraw.Draw(img)
      w, h = img.size
      banner_h = int(h * 0.05)
      draw.rectangle([(0, 0), (w, banner_h)], fill=(220, 20, 60))
      now_str = datetime.datetime.now().strftime("%H:%M:%S %d/%m")
      text_str = f"[MAY {machine}] - {now_str}"
      try:
          font = ImageFont.truetype("arial.ttf", int(banner_h * 0.55))
      except Exception:
          font = ImageFont.load_default()
      draw.text((30, int(banner_h * 0.2)), text_str, fill=(255, 255, 255), font=font)
      img.save(saved_img_path, format="PNG")
  ```

## 2. Quy tắc Giữ Hiện Trường Lỗi & Device Lock
- Khi máy gặp lỗi trong lúc chạy batch hoặc on-demand: **GIỮ NGUYÊN HIỆN TRƯỜNG MÀN HÌNH LỖI** và **GIỮ NGUYÊN DEVICE LOCK (`DEVICE_LOCK_PRESENT`)**.
- CẤM tự ý chạy lệnh cleanup hàng loạt (`force-stop`, `input keyevent KEYCODE_HOME`) làm mất trạng thái màn hình lỗi trước khi user kiểm tra.

## 3. Xử lý màn hình Đăng nhập nhanh / Cache tài khoản rác (Fast Login One-Tap)
- **Hiện tượng**: App TikTok mở ra màn "Tiếp tục với tên @username_la" kèm nút "Sử dụng tài khoản khác".
- **Kiểm tra**: Quét đối chiếu handle đó với các file Excel tracking (`taikhoan_dat_v2_updated .xlsx`, `Tik1.xlsx`...):
  - Nếu nick **KHÔNG CÓ** trong Excel farm: Đây là session cache rác cũ.
  - Thao tác: Bấm nút ba chấm `...` ở góc trên bên phải -> Chọn **"Xóa tài khoản"** (Delete account) để xóa sạch session rác khỏi app, hoặc bấm **"Sử dụng tài khoản khác"** để tiếp tục luồng đăng ký tài khoản mới.

## 4. Xử lý kẹt màn hình Đặt Biệt danh / Đổi Tên (0/30)
- **Hiện tượng**: Máy đã nhập OTP thành công nhưng kẹt ở màn hình nhập "Tên" (`0/30`).
- **IME bắt buộc**: Phải kích hoạt đúng IME `com.github.uiautomator/.AdbKeyboard` trước khi broadcast `ADB_KEYBOARD_INPUT_TEXT` với chuỗi Base64 tiếng Việt:
  ```bash
  adb -s <serial> shell ime enable com.github.uiautomator/.AdbKeyboard
  adb -s <serial> shell ime set com.github.uiautomator/.AdbKeyboard
  adb -s <serial> shell am broadcast -a ADB_KEYBOARD_INPUT_TEXT --es text <base64_name>
  ```
- Sau khi gõ tên tiếng Việt vào ô input: Tap nút **"Lưu"** ở góc phải trên `(990, 138)` -> Tap **"Xác nhận"** `(750, 1175)` nếu có pop-up cảnh báo đổi tên 7 ngày -> Trở về tab Hồ sơ để trích xuất ID tài khoản.
