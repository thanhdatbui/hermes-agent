# Farm Alert Screencap Banner & State Lock Protocol (2026-08-24)

## 1. Quy tắc bắt buộc khi gửi ảnh màn hình lỗi máy Farm (Farm Alert Banner)
- **CẤM gửi ảnh màn hình trơn không có số máy.**
- Mọi ảnh screencap khi báo cáo lỗi cho user / Telegram bắt buộc phải chèn **Banner Đỏ ở đỉnh ảnh** với format:
  `[MAY X] - HH:MM:SS dd/mm`
  (Theo chuẩn của `automation_core.alerts.send_farm_machine_alert`).
- Chiều cao banner: ~5% chiều cao ảnh (`banner_h = int(h * 0.05)`), nền đỏ `(220, 20, 60)`, chữ trắng font rõ ràng.
- Gửi ảnh qua `MEDIA:<path>` ở **DÒNG RIÊNG**, không bọc markdown.

```python
import io, datetime
from PIL import Image, ImageDraw, ImageFont

img = Image.open(io.BytesIO(proc.stdout)).convert('RGB')
draw = ImageDraw.Draw(img)
w, h = img.size
banner_h = int(h * 0.05)
draw.rectangle([(0, 0), (w, banner_h)], fill=(220, 20, 60))
now_str = datetime.datetime.now().strftime('%H:%M:%S %d/%m')
text_str = f'[MAY {machine_stt}] - {now_str}'
try:
    font = ImageFont.truetype('arial.ttf', int(banner_h * 0.55))
except Exception:
    font = ImageFont.load_default()
draw.text((30, int(banner_h * 0.2)), text_str, fill=(255, 255, 255), font=font)
img.save(saved_img_path, format='PNG')
```

## 2. Quy tắc Giữ Hiện Trường & Device Lock khi Lỗi
- Khi script chạy gặp lỗi hoặc timeout:
  1. **KHÔNG** chạy lệnh dọn dẹp hàng loạt (`force-stop`, `KEYCODE_HOME`) làm mất hiện trường lỗi.
  2. **GIỮ NGUYÊN LOCK THIẾT BỊ** (`DEVICE_LOCK_PRESENT` / `locked_by_user_reg_flow`) trên cả 2 thư mục lock:
     - `C:\Users\Kibe\.codex\device-locks`
     - `C:\Users\Kibe\AppData\Local\Taadaa\device-locks`
  3. Chụp ảnh màn hình có Banner Đỏ gửi cho user kèm mô tả ngắn gọn và đề xuất xử lý.
  4. Dừng lại chờ user hướng dẫn / duyệt trước khi thao tác tiếp.

## 3. Preflight Live Proxy Gate cho Batch Reg / Tasks
- Luôn kiểm tra broadcast `vn.vichanger.app.GET_IP` (`result=200`) và `tun0 UP`.
- So sánh IP với Direct Host IP (`https://api.ipify.org` - vd `1.53.114.53`). Nếu trùng hoặc `result=0` / timeout $\rightarrow$ loại ngay khỏi danh sách chạy, tuyệt đối không chạy để tránh lộ dải IP farm.

## 4. Chuẩn hóa Bàn phím AdbKeyboard & Xóa Session rác
- **AdbKeyboard:** Ngoại trừ repo `register gmail` dùng SamsungKeypad cho Google flow, toàn bộ các repo khác (`Tiktok_Reg`, `Hotmail`, `tiktok-log-in`, `add mail khoi phuc`) dùng `com.github.uiautomator/.AdbKeyboard` qua broadcast base64 UTF-8.
- **Xóa session rác màn One-Tap:** Khi gặp màn hình *"Tiếp tục với tên @..."*, đối chiếu với toàn bộ kho Excel. Chỉ xóa khi nick **KHÔNG CÓ** trong bất kỳ file Excel nào.
