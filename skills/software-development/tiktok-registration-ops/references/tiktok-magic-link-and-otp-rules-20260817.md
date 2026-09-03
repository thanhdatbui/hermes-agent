# TikTok Magic Link vs OTP Handling & Session Rules (2026-08-17)

## 1. Phân biệt rõ rệt Màn OTP vs Màn Magic Link

| Đặc điểm | Màn OTP | Màn Magic Link |
|---|---|---|
| **Tiêu đề** | "Nhập mã gồm 6 chữ số" | "Kiểm tra hộp thư của bạn" |
| **Nội dung** | "Để đặt mật khẩu, hãy nhập mã gồm 6 chữ số..." | "Bạn có thể đăng ký bằng liên kết được gửi đến..." |
| **Input fields** | 6 ô vuông nhập số + bàn phím số | KHÔNG có ô nhập mã, không có bàn phím số |
| **Nút Resend** | "Gửi lại mã 32s" / "Gửi lại mã" | "Gửi lại email" / "Gửi lại liên kết" |
| **Cách xử lý** | Đọc mã 6 số từ Graph API / Hotmail token -> Gõ vào 6 ô input | Mở mail TikTok -> Bấm nút đỏ "Xác minh email" -> Deeplink tự mở app TikTok |

> ⚠️ **Chống nhầm:** Chữ `"Gửi lại email"` (magic link) KHÔNG được match nhầm với `"Gửi lại mã"` (OTP). `success_hints` không được chứa `"Hộp thư"/"Hop thu"` vì sẽ match nhầm màn "Kiểm tra hộp thư của bạn" thành login thành công.

---

## 2. Quy luật sống còn của TikTok Magic Link Session (CRITICAL)

Khi TikTok hiển thị màn hình "Kiểm tra hộp thư của bạn", TikTok sinh ra một **Ticket phiên đăng ký/xác thực tạm thời trong RAM** của Activity `SignUpOrLoginActivity`.

- **CẤM TUYỆT ĐỐI force-stop hoặc close recent app TikTok:**
  Nếu app TikTok bị kill hoặc đóng khỏi Recent Apps, Ticket phiên trong RAM bị hủy. Khi deeplink được gọi (từ Chrome/Samsung Internet hoặc Intent), TikTok mở lại ở cold-start và sẽ từ chối xác thực, hiển thị popup lỗi:
  > *"Đã xảy ra lỗi. Hãy đảm bảo sử dụng cùng thiết bị bạn đã sử dụng để gửi email xác minh."*
- **Quy trình chuẩn:** 
  1. Giữ nguyên app TikTok ở background tại màn hình "Kiểm tra hộp thư của bạn".
  2. Mở Outlook / Graph API lấy deeplink URL.
  3. Bấm nút đỏ trong mail hoặc kích hoạt Intent deeplink để app TikTok đang chạy ngầm tiếp nhận callback và chuyển màn tiếp theo (DOB / Password).

---

## 3. Outlook WebView & Nút "Xác minh email"

- **Đặc điểm UI Outlook Reading Pane:**
  Nội dung email trong Outlook hiển thị dưới dạng WebView. `uiautomator dump` thường KHÔNG bóc tách được các node con bên trong WebView (XML length ngắn ~9KB, không có node `rid="link"` hay text "Xác minh email").
- **Cách bấm nút:**
  - Nút đỏ "Xác minh email" trên màn hình chuẩn 1080x1920 có tâm ở tọa độ **`(540, 1460)`**.
  - Gọi ATX JSON-RPC click trực tiếp tọa độ `(540, 1460)` thay vì phụ thuộc vào XML parse.
- **Modal "Ghi chú nhanh về tài khoản Microsoft":**
  - XML chỉ chứa text `"Inapp UnifiedConsent"`.
  - Nút "OK" ở dưới cùng có tâm tại tọa độ **`(540, 1704)`**.
  - Phải swipe lên nhẹ rồi ATX click `(540, 1704)` để dismiss modal trước khi vào Hộp thư đến.

---

## 4. File Lock / PermissionError khi đọc Workbook

- Nếu file workbook nguồn (`gmail_clean_v2.xlsx` / `taikhoan_dat_v2_updated .xlsx`) đang được mở bằng ứng dụng Excel trên Windows:
  - Python `openpyxl` / `shutil` sẽ bị văng lỗi `PermissionError: [Errno 13] Permission denied`.
  - Hàm `resolve_graph_credentials` bị fail ngầm -> script tưởng không có Graph token -> fallback sai sang đọc Outlook app.
- **Xử lý:** Kiểm tra process Excel (`wmic process where "Name='excel.exe'" get ProcessId,CommandLine`) và yêu cầu đóng file trước khi chạy batch.
