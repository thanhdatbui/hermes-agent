# Kỷ Luật Dọn Tab Trình Duyệt CDP & Tính Bền Vững Của Cookie (CDP Tab Hygiene & Cookie Lifecycle)

## 1. Tính Bền Vững Của Cookie Khi Đóng Tab
- **Đóng tab KHÔNG BAO GIỜ làm mất Cookie hay phiên đăng nhập:**
  - Toàn bộ Cookie, Token xác thực, LocalStorage, IndexedDB và Session state đều được Chrome lưu tập trung tại cơ sở dữ liệu trên đĩa (`User Data/<Profile>/Network/Cookies`).
  - Dữ liệu này tồn tại độc lập với số lượng và trạng thái của các tab đang mở.
  - Khi đóng tab, Chrome chỉ hủy tiến trình dựng hình (Render Process), giải phóng ngay từ **80MB đến 200MB RAM** và CPU cho hệ thống.
  - Khi mở lại domain đó ở tab mới, Chrome tự động nạp lại Cookie và duy trì trạng thái đăng nhập nguyên vẹn.

## 2. Nguyên Nhân Gây Tích Tụ Tab Rác (Orphaned Tabs)
- Các script tự động hóa (CDP / Playwright / Puppeteer) khi mở tab để bóc OTP, giải captcha hoặc kiểm tra trang web thường gọi `Target.createTarget` hoặc `browser.newPage()`.
- Nếu script gặp lỗi ngoại lệ (exception), crash, bị ngắt giữa chừng hoặc thiếu khối dọn dẹp, các tab này không được đóng lại và tích tụ thành hàng chục tab chạy nền, gây treo và nặng máy.

## 3. Kỷ Luật Viết Code Automation
- **Bắt buộc dùng `try ... finally`:** Mọi đoạn code mở tab phụ / tab tạm thời bắt buộc phải có lệnh đóng tab trong khối `finally`:
  ```python
  new_page = await context.new_page()
  try:
      # Thực hiện lấy OTP / kiểm tra
      ...
  finally:
      await new_page.close()
  ```

## 4. Dọn Dẹp Tab Rác Từ Xa Qua HTTP CDP API
- Endpoint quản lý tab của Chrome CDP (mặc định cổng 9222):
  - **Lấy danh sách tất cả các tab:**
    `GET http://127.0.0.1:9222/json`
  - **Đóng 1 tab cụ thể theo target id:**
    `GET http://127.0.0.1:9222/json/close/{target_id}`
- **Quy tắc an toàn khi dọn:**
  - Chỉ đóng các tab rác: URL `about:blank`, tab lỗi 404, tab chứa domain giải captcha (CapMonster, 2Captcha, OMOCaptcha).
  - TUYỆT ĐỐI KHÔNG đóng các tab làm việc chính của User (BoxTaiKhoan, Shopee, Gmail, v.v.).
