# Cạm Bẫy Dump XML / Tọa Độ Mù Trên Giao Diện TikTok Settings & Quy Chuẩn WinRT OCR Bắt Buộc

## 1. Hiện Trường Thảm Họa Thực Tế (2026-10-31)
Trong tác vụ tự động đổi Hotmail thay thế Gmail DIE trên app TikTok (Samsung S7 farm):
- **Sai lầm kiến trúc:** Agent tự chế script ad-hoc dùng `atx_rpc('dumpWindowHierarchy')` XML thay vì gọi module chuẩn `automation_core.ui_extract.extract_ui` (WinRT OCR).
- **Hệ quả phần cứng:** Chip Exynos 8890 trên Samsung S7 bị nghẽn binder/CPU, trả về XML rỗng hoặc lag. Script rơi vào nhánh fallback dùng tọa độ cứng `[540, 1810]` sát đáy màn hình.
- **Thảm họa bấm nhầm:** Trên màn hình *Cài đặt và quyền riêng tư -> Tài khoản* của TikTok, mục *"Thông tin tài khoản"* nằm ở đỉnh (`y ≈ 320`), còn mục nằm ở đáy (`y = 1810`) chính là **`Hủy kích hoạt hoặc xóa tài khoản`**! Bot bấm trúng và nhảy thẳng vào màn hình chọn *"Xóa tài khoản vĩnh viễn"*.
- **Ảo giác báo cáo mù:** Khi màn hình hiện form hủy kích hoạt, Agent lại không chạy WinRT OCR đọc chữ mà phán đoán mù là "Dính Captcha Puzzle Slider", gây bức xúc nghiêm trọng cho User khi User trực tiếp kiểm tra thấy máy đang ở trang xóa nick.

## 2. Invariant Cưỡng Chế Bắt Buộc (UI-OCR-TIKTOK-SETTINGS)

### A. Cấm Tuyệt Đối Tọa Độ Cứng & Dump XML Trong Settings
1. **CẤM TUYỆT ĐỐI:** Bất kỳ tọa độ pixel cứng nào (như `[540, 1810]`, `[540, 320]`, `[136, 480]`) trên các menu Settings, Tài khoản, Thông tin tài khoản của TikTok.
2. **CẤM TUYỆT ĐỐI:** Gọi `dumpWindowHierarchy` hoặc `uiautomator dump` trên các màn hình này.

### B. Quy Trình Bắt Buộc: WinRT OCR Primary
1. Mọi bước điều hướng trong Settings BẮT BUỘC chụp ảnh `adb exec-out screencap -p` và gọi WinRT OCR (`ocr_screen_boxes` / `extract_ui`).
2. Tìm đúng text mục tiêu (`"Thông tin tài khoản"`, `"Email"`, `"Thay đổi email"`) và click vào tâm box OCR `((x1+x2)//2, (y1+y2)//2)`.

### C. Fail-Safe Guard Chống Xóa Nick
Trước khi thực hiện bất kỳ lệnh click nào trên màn hình Tài khoản/Cài đặt:
```python
boxes = ocr_screen_boxes(screenshot_path)
for text, bounds in boxes:
    if any(k in text.lower() for k in ["xóa", "hủy kích hoạt", "delete", "deactivate"]):
        # PHÁT HIỆN DẤU HIỆU TRANG XÓA TÀI KHOẢN -> BẤM BACK / HOME NGAY LẬP TỨC!
        atx_rpc(base_url, "pressKey", ["back"])
        raise SafetyAbortError(f"Phát hiện màn hình nguy hiểm '{text}' - Đã bấm Back thoát khẩn cấp!")
```

### D. Không Báo Cáo Captcha Nếu Chưa Có Bằng Chứng WinRT OCR
Cấm kết luận "dính Captcha" hoặc "bị challenge" nếu WinRT OCR trên ảnh chụp hiện trường không bóc tách được các từ khóa: `xác minh`, `captcha`, `puzzle`, `khớp hình`, `drag`.
