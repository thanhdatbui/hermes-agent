# Tích hợp Fast OCR Popup Dismissal cho Benign Popup Registry (17/10/2026)

## 1. Bối cảnh & Mục tiêu
Trong quá trình nuôi tài khoản TikTok (`tiktok-luot nuoi acc`), việc đọc cây XML phân cấp của Android tốn từ 3–15 giây và dễ vỡ khi ứng dụng obfuscate ID giao diện. 
Khoảng 90% popup xuất hiện trong chu trình lướt video là các popup lành tính có nút đóng quen thuộc (`"Để sau"`, `"Không phải bây giờ"`, `"Hủy"`, `"Đóng"`, `"Not now"`).
Việc tích hợp OCR WinRT (`automation_core.ocr`) cho phép quét và dập popup siêu tốc trong vòng **0.3 giây**, không làm đứt nhịp nuôi video của farm.

## 2. Kiến trúc Handler trong `benign_popup_registry.py`
Handler được đăng ký với độ ưu tiên cao (`priority: 85`):
```python
register_popup_handler(
    RegistryEntry(
        "ocr_fast_popup_dismiss",
        85,
        _detect_ocr_fast_popup,
        _dismiss_ocr_fast_popup,
        True,
        "manual",
    )
)
```

### A. Detector `_detect_ocr_fast_popup`:
- Sử dụng `parse_ocr_boxes_output(ocr_text)` để chuyển đổi đầu ra dạng `x1,y1,x2,y2\ttext` thành danh sách boxes.
- Gọi `find_popup_dismiss_button_ocr(boxes)`:
  - **Cầu dao an toàn (Fail-Closed):** Tự động từ chối xử lý (`return False`) nếu phát hiện bất kỳ từ khóa nhạy cảm nào: `"Mật khẩu"`, `"Captcha"`, `"Đăng nhập"`, `"Thanh toán"`, `"OTP"`, v.v.
  - Khớp các nút bấm lành tính và trả về tọa độ `(cx, cy)` của nút đóng.

### B. Dismisser `_dismiss_ocr_fast_popup`:
- Thực hiện chụp ảnh màn hình qua `ctx.adb.exec_out(["screencap", "-p"], timeout=15)`.
- Ghi tạm file PNG và chạy `ocr_screen_boxes(png_path)` để lấy tọa độ mới nhất ngay tại thời điểm click.
- Thực hiện tap dập popup qua `_perform_click_target(ctx, tap_pt)`.
- **Kỷ luật dọn dẹp tempfile:** File ảnh tạm bắt buộc phải được `os.unlink()` xóa sạch trong khối `finally:` để chống tràn đĩa.

## 3. Kiểm chứng thực tế
```python
from flows.benign_popup_registry import BENIGN_POPUP_REGISTRY, _detect_ocr_fast_popup

# Khớp đúng popup lành tính:
sample_ocr = '100,500,400,560\tĐể sau'
assert _detect_ocr_fast_popup('', sample_ocr) is True

# Từ chối dập khi có từ khóa nhạy cảm:
sample_sensitive = '100,500,400,560\tĐể sau\n100,200,400,260\tMật khẩu'
assert _detect_ocr_fast_popup('', sample_sensitive) is False
```
