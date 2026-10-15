# OmniRoute Dashboard Blank / Empty Page Recovery & Backend-Only Trap

## 1. Phân biệt độc lập giữa 9Router (:20128) và OmniRoute (:20129)
- **Port 20128 (9Router)**: Có UI Dashboard riêng (`http://127.0.0.1:20128/dashboard`).
- **Port 20129 (OmniRoute Core)**: **CŨNG CÓ DASHBOARD UI RIÊNG** (`http://127.0.0.1:20129/dashboard` hoặc `/home`).
- **CẤM TUYỆT ĐỐI**: Khi người dùng hỏi hoặc báo lỗi trang OmniRoute (20129) không vào được, CẤM bảo người dùng sang 20128 hay nhầm lẫn hai dịch vụ với nhau.

## 2. Nguyên nhân "Trang trắng" (Empty Page) trên Port 20129
Khi truy cập `http://127.0.0.1:20129/dashboard` mà trình duyệt chỉ nhận được mã HTML rỗng:
```html
<html lang="en"><head>...</head><body><div hidden=""><!--$--><!--/$--></div>...</body></html>
```
- **Thủ phạm**: Trước đó có agent hoặc quy trình chạy lệnh:
  ```bash
  npm run build:backend
  # hoặc cờ OMNIROUTE_BUILD_BACKEND_ONLY=1 / OMNIROUTE_BUILD_PROFILE=backend
  ```
- **Cơ chế gây lỗi**: `scripts/build/backendOnlyPages.mjs` cố tình thay thế toàn bộ ~126 page/layout của Next.js bằng stub `return null;` (`BackendOnlyPageStub`) để tạo bản build headless siêu nhẹ chỉ chạy REST API.
- Bản build này ghi đè vào `.build/next/`. Khi OmniRoute khởi động lại, API backend vẫn sống nhưng giao diện Web UI bị biến thành trang trắng hoàn toàn.

## 3. Quy trình khôi phục giao diện OmniRoute đầy đủ (Standard Recovery)
1. **Kiểm tra source code gốc**:
   Source code trong `C:\Users\Kibe\OmniRoute\src\app` thường không bị mất vì stubs được auto-restore sau khi build xong. Xác nhận không có marker `omniroute:backend-only-stub` trong code gốc.
2. **Chạy Build đầy đủ (Full Build)**:
   Xóa bỏ biến môi trường `OMNIROUTE_BUILD_BACKEND_ONLY` và `OMNIROUTE_BUILD_PROFILE`.
   Chạy lệnh build Next.js đầy đủ:
   ```bash
   cd C:\Users\Kibe\OmniRoute
   node scripts/build/build-next-isolated.mjs
   # hoặc npm run build
   ```
   *Quá trình compile đầy đủ App Router bằng Turbopack mất khoảng 1.5 - 3 phút.*
3. **Restart OmniRoute PID trên port 20129**:
   Hạ PID cũ đang giữ port 20129 để `omniroute_watchdog.ps1` tự động kích hoạt process mới với artifact vừa build:
   ```powershell
   Stop-Process -Id (Get-NetTCPConnection -LocalPort 20129 -State Listen).OwningProcess -Force
   ```
4. **Hậu kiểm**:
   - `http://127.0.0.1:20129/api/health` trả về `{"status":"ok"}`.
   - Dùng `browser_navigate` và `browser_vision` mở `http://127.0.0.1:20129/dashboard` soi mắt kiểm tra dashboard hiển thị đầy đủ giao diện, sidebar, và nội dung.
