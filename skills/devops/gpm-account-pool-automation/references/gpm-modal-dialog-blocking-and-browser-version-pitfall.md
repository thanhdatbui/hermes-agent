# GPM Modal Dialog Blocking & Pseudo Browser Version Errors

## 1. Hiện tượng & Triệu chứng
- Khi gọi GPM Local API `GET /api/v3/profiles/start/<profile_id>`, API trả về thông báo lỗi:
  ```json
  {"success": false, "data": null, "message": "Yêu cầu cập trình duyệt [Chromium] [142]"}
  // hoặc [Chromium] [127]
  ```
- Kiểm tra trong thư mục `C:/Users/Kibe/AppData/Local/Programs/GPMLogin/gpm_browser/` thấy thư mục `gpm_browser_chromium_core_142/142.0.7444.163` hoặc `gpm_browser_chromium_core_127` ĐÃ TỒN TẠI đầy đủ binary `chrome.exe`, `chrome.dll`, `gpmdriver.exe`.
- Update browser version qua API bị chặn (`Do not downgrade from version 137`).

## 2. Root Cause
- **Modal Popup Block:** Khi GPMLogin có popup modal thông báo trên UI (ví dụ popup **"Big Update"** giới thiệu phiên bản mới, tính năng Fingerprint 411, announcement), toàn bộ backend engine của app GPM bị treo ở trạng thái chờ người dùng tương tác.
- Trong trạng thái modal overlay này, mọi request gọi tới API `/start/<id>` đều bị GPM trả về mã lỗi giả: `Yêu cầu cập trình duyệt [Chromium] [XXX]`.
- File `do_not_show_what_news` có thể bị app ghi đè lại sau khi restart.
- App GPMLogin thường chạy dưới quyền Administrator (elevated process), nên các lệnh Win32 simulate mouse/keyboard từ unprivileged background worker bị Windows UIPI/UAC chặn (`Access is denied`).

## 3. Cách chẩn đoán & Xử lý chuẩn
1. **Chẩn đoán:**
   - Chụp nhanh cửa sổ GPM qua PowerShell/GDI PrintWindow hoặc inspect window:
     Kiểm tra xem trên màn hình GPM có đang hiện popup modal ("Big Update", thông báo update, dialog hỏi ý kiến) hay không.
   - Tuyệt đối KHÔNG kết luận máy thiếu core Chromium hay vội vã đi tải/xóa binary khi chưa inspect màn hình.
2. **Xử lý:**
   - Bấm nút đóng modal (ví dụ nút đỏ **"Đóng thông báo"**) trên giao diện GPMLogin.
   - Ngay sau khi modal được đóng, API `/api/v3/profiles/start/<id>` sẽ lập tức trả về `success: true` và launch profile bình thường mà không cần sửa đổi file hay cấu hình profile.
