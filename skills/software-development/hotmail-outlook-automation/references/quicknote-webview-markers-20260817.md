# QuickNote & Reading Pane WebView Markers (2026-08-17)

## 1. QuickNote Modal (Inapp UnifiedConsent)
- Tiêu đề modal: `Ghi chú nhanh về tài khoản Microsoft của bạn`
- Nút bấm: `OK` tại tâm `(540, 1704)` trên màn hình 1080x1920.
- `uiautomator dump` không bóc tách được text tiếng Việt trong dialog này mà chỉ thấy class/label `Inapp UnifiedConsent`.
- Cần nhận diện bằng marker `"inapp unifiedconsent"` kết hợp kiểm tra hiển thị nút `OK`.

## 2. Quy tắc chuẩn hóa tiếng Việt chứa chữ "đ"
- NFD `unicodedata.normalize('NFD', s)` chỉ tách dấu thanh của nguyên âm (a, e, o, u, i, y).
- Ký tự `đ` (U+0111) là phụ âm độc lập, **không bị tách thành `d`**.
- Do đó `hàng đầu` -> `hang đau` (vẫn giữ nguyên `đ`). Mọi marker regex/substring so khớp với chuỗi sau khi strip combining marks bắt buộc phải giữ `đ`.

## 3. WebView Reading Pane Outlook
- Nội dung mail xác minh TikTok hiển thị qua WebView.
- Nút "Xác minh email" màu đỏ nằm ở tâm `(540, 1460)`.
- Khi uiautomator dump không trích xuất được `node resource-id="link"`, bắt buộc phải có fallback click trực tiếp vào tọa độ `(540, 1460)` qua ATX JSON-RPC hoặc `adb shell input tap`.
