# MikroTik Web Manager Startup Headless & Anti-Browser Spam Pattern

## 1. Triệu chứng & Vấn đề (Problem)
- Mỗi khi khởi động máy trạm Kibe hoặc khi tiến trình MikroTik Web Manager được khởi chạy lại, trình duyệt Google Chrome tự động bật lên 1 tab mới trỏ tới `http://localhost:2310` (hoặc `http://kibe:2310`).
- Nếu tiến trình được watchdog quản lý hoặc máy khởi động định kỳ theo ca (11:20, 17:20, 05:20), người dùng sẽ bị tích tụ hàng loạt tab Chrome rác ("spam 1 nùi tab").

## 2. Nguyên nhân gốc rễ (Root Cause)
- Trong thư mục Windows Startup (`%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup`), file `mikrotik_web.vbs` gọi `D:\Taadaa\AI-Tools\tools\mikrotik_web\run_hidden.vbs` để chạy `server.py` cổng 2310.
- Trong mã nguồn `tools/mikrotik_web/server.py` tại hàm `main()`, tác giả cũ đã hardcode lệnh:
  ```python
  import webbrowser
  try:
      webbrowser.open(f"http://localhost:{port}")
      print(f"[*] Opening browser...")
  except Exception:
      print(f"[*] Open http://localhost:{port} in your browser")
  ```
- Lệnh này kích hoạt trình duyệt mặc định của hệ điều hành mở URL cục bộ ngay khi tiến trình lắng nghe port 2310 thành công.

## 3. Quy chuẩn Khắc phục & Bất biến (Invariants)
1. **Dịch vụ nền bắt buộc Headless:**
   - Các công cụ quản trị hạ tầng, proxy, web UI nội bộ (`server.py` cổng 2310, `dashboard.py` cổng 1905, v.v.) khi chạy dạng background service / Windows Startup BẮT BUỘC phải hoạt động hoàn toàn headless.
   - **CẤM TUYỆT ĐỐI** gọi các hàm tương tác giao diện người dùng như `webbrowser.open()`, `os.system('start chrome ...')` trong luồng khởi động (`main()`) của server daemon.
2. **Quy chuẩn sửa mã nguồn:**
   - Xóa bỏ hoàn toàn khối lệnh `webbrowser.open(...)` trong hàm `main()`.
   - Giữ nguyên luồng log console: chỉ in thông tin URL ra stdout/stderr để người vận hành chủ động truy cập khi cần thiết:
     ```python
     print(f"[*] MikroTik Web UI available at http://localhost:{port}")
     ```
3. **Quy trình áp dụng bản vá:**
   - Sử dụng `unified_patch_pipeline.py` đối với repo `D:/Taadaa/AI-Tools`.
   - Kiểm chứng biên dịch cú pháp bằng `python -m py_compile tools/mikrotik_web/server.py`.
