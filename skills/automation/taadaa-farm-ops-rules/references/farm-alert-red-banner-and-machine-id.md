# Quy tắc Báo Cáo Ảnh Máy Farm (Farm Alert Red Banner & Machine ID)

## Bối Cảnh & Lý Do
User yêu cầu nghiêm ngặt ở cấp độ ALL repo: Khi gửi ảnh chụp màn hình máy farm bị lỗi / cần kiểm tra / hỏi hướng dẫn, **CẤM TUYỆT ĐỐI gửi ảnh màn hình trơn không có định danh số máy**.

Khi gửi hàng loạt 5-20 ảnh máy lên chat Telegram, nếu không có banner số máy dán trực tiếp lên ảnh, user và agent không thể phân biệt được ảnh nào thuộc về máy nào (nhất là khi các màn hình lỗi trông tương tự nhau).

## Quy Chuẩn Render Banner Đỏ Lên Ảnh (Pillow / PIL)
Mọi thao tác chụp ảnh screencap khi báo cáo cho user phải vẽ dải Banner Đỏ trên cùng:
- **Màu sắc:** Đỏ tươi/đỏ cảnh báo `RGB(220, 20, 60)`.
- **Kích thước:** Chiều cao banner chiếm khoảng `5%` chiều cao ảnh (`banner_h = int(h * 0.05)`).
- **Nội dung chữ:** `[MAY <số_máy>] - HH:MM:SS dd/mm` (Chữ in hoa màu trắng `(255, 255, 255)`).
- **Cơ chế:** Tương tự `send_farm_machine_alert` trong `automation_core.alerts`.

```python
import io, datetime
from PIL import Image, ImageDraw, ImageFont

def annotate_farm_machine_alert_banner(screencap_bytes: bytes, machine_num: int) -> bytes:
    img = Image.open(io.BytesIO(screencap_bytes)).convert("RGB")
    draw = ImageDraw.Draw(img)
    w, h = img.size
    banner_h = int(h * 0.05)
    draw.rectangle([(0, 0), (w, banner_h)], fill=(220, 20, 60))
    now_str = datetime.datetime.now().strftime("%H:%M:%S %d/%m")
    text_str = f"[MAY {machine_num}] - {now_str}"
    try:
        font = ImageFont.truetype("arial.ttf", int(banner_h * 0.55))
    except Exception:
        font = ImageFont.load_default()
    draw.text((30, int(banner_h * 0.2)), text_str, fill=(255, 255, 255), font=font)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
```

## Bắt Buộc Giữ Nguyên Hiện Trường & Lock Máy
- Khi batch / task reg / feed / follow gặp lỗi:
  1. **GIỮ NGUYÊN MÀN HÌNH HIỆN TRƯỜNG LỖI** (Không tự ý đóng app `force-stop`, không ấn `KEYCODE_HOME` về màn hình chính làm mất dấu vết lỗi).
  2. **GIỮ LOCK THIẾT BỊ** (`DEVICE_LOCK_PRESENT` / `FAILED_LOCKED`).
  3. Screencap có vẽ banner đỏ `[MAY X]` -> Gửi file `MEDIA:<đường_dẫn>` dòng riêng cho user.
  4. Dùng `vision_analyze` đọc ảnh trước và đề xuất giải pháp cho user.
