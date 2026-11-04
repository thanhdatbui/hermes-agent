---
name: headless-desktop-window-scraping
description: "Trích xuất ảnh và cuộn điều khiển ứng dụng Windows (Electron, Zalo, GPM) trong môi trường nền/màn hình khóa qua Win32 PrintWindow & PostMessage."
---
# Headless & Locked-Session Desktop Window Scraping

Sử dụng kỹ thuật này khi cần trích xuất dữ liệu, chụp màn hình hoặc cuộn điều khiển các ứng dụng Windows (Zalo PC, Electron apps, GPM, trình duyệt) trong môi trường chạy ngầm, không có tương tác chuột vật lý hoặc máy tính đang khóa màn hình (`workstation locked`).

## 1. Cạm Bẫy Môi Trường Màn Hình Khóa (Headless / Locked Session Traps)
- **Bẫy `ImageGrab.grab()` & `CopyFromScreen`:** Trong phiên nền hoặc khi màn hình tắt/khóa, gọi `ImageGrab.grab(bbox=...)` sẽ quăng lỗi `OSError: screen grab failed`. `Graphics.CopyFromScreen` sẽ quăng lỗi `Win32Exception: The handle is invalid`.
- **Bẫy `BitBlt` từ Desktop DC (`GetDC(0)`):** Hàm trả về thành công nhưng toàn bộ pixel ảnh là màu đen tuyền (`[0, 0, 0]`).
- **Bẫy `SetCursorPos` & `mouse_event` / `keybd_event`:** Hệ điều hành Windows âm thầm bỏ qua (silently drop) mọi lệnh di chuyển chuột hoặc nhấn phím vật lý khi phiên không phải là interactive desktop console đang active.

---

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
