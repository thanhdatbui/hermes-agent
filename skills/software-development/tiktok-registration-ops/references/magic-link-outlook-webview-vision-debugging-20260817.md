# Magic Link & Outlook WebView Automation Lessons (2026-08-17)

## 1. Magic Link vs Numeric OTP Screen Distinction (TikTok)
| Tiêu chí | Màn Magic Link | Màn OTP số (Numeric) |
|---|---|---|
| **Tiêu đề** | `Kiểm tra hộp thư của bạn` | `Nhập mã gồm 6 chữ số` / `Xác minh email` |
| **Mô tả** | `Bạn có thể đăng ký bằng liên kết được gửi đến...` | `Để đặt mật khẩu, hãy nhập mã gồm 6 chữ số...` |
| **Nút bấm** | `Gửi lại email` (Resend email) | `Gửi lại mã [XXs]` (Resend code) |
| **Input** | KHÔNG có ô nhập mã, không có bàn phím | 6 ô vuông nhập mã + bàn phím số |

> ⚠️ **CỰC KỲ QUAN TRỌNG:**
> - `gui lai EMAIL` != `gui lai MA`.
> - **PITFALL `success_hints`:** Tuyệt đối KHÔNG để `"Hộp thư"`, `"Hop thu"`, `"Inbox"` trong danh sách `success_hints` của hàm `wait_login_success`. Màn chờ "Kiểm tra hộp thư của bạn" sẽ bị match nhầm là đã login thành công, dẫn tới script tự chuyển sang tab Profile và bấm nhầm vào nút "Gửi lại email"!

---

## 2. Outlook WebView & QuickNote (Ghi chú nhanh / UnifiedConsent)
- **Đặc điểm WebView Outlook:** Nội dung email và một số popup consent của Microsoft chạy trong WebView/Reading Pane. `uiautomator dump` XML thường không bóc tách được node con, chỉ thấy `Inapp UnifiedConsent` hoặc XML cụt (9-10KB).
- **Quy tắc Marker tiếng Việt có chữ `đ`:** `unicodedata.normalize('NFD', ...)` chỉ bóc tách các dấu thanh (sắc, huyền, hỏi, ngã, nặng), **KHÔNG bóc tách chữ `đ` thành `d`**. Vì vậy `hàng đầu` sau khi strip combining accents là `hang đau` (vẫn còn `đ`). Sửa `đ` thành `d` sẽ làm hỏng toàn bộ marker detection!
- **Modal Ghi chú nhanh (Quick Note):** 
  - Thường chặn ngay sau khi mở Outlook.
  - Tọa độ nút **"OK"**: trung tâm `(540, 1704)` trên màn hình 1080x1920.
  - Phải dùng `adb forward tcp:7912 tcp:7912` ở cấp host (qua `subprocess.run`), KHÔNG gọi qua `adb shell exec-out forward` vì trên Android device không có lệnh `forward`.

---

## 3. Bấm nút "Xác minh email" trong Email TikTok (Outlook WebView)
1. Thử parse XML tìm node `resource-id="link"` + `clickable="true"` + desc chứa `"xac minh"`.
   - *Lưu ý:* Tuyệt đối không match theo text đơn thuần vì text `"Xác minh email của bạn"` có trong cả subject/title (node không clickable).
2. **Fallback Click Tọa Độ Trực Tiếp:** Nếu XML WebView không trả về node link con, bấm trực tiếp vào tọa độ tâm nút đỏ `(540, 1460)` qua ATX JSON-RPC hoặc `input tap`.

---

## 4. Image-Driven Debugging & Tự Đọc Ảnh (User Rule)
- Khi chụp ảnh màn hình máy thiết bị để chẩn đoán:
  1. Agent **BẮT BUỘC dùng vision (`vision_analyze`) để tự đọc và phân tích toàn bộ nội dung ảnh trước**.
  2. Báo cáo rõ màn hình là gì, phân tích tọa độ, đề xuất phương án xử lý.
  3. Gửi ảnh cho user theo đúng format (dòng riêng đầu tiên `MEDIA:C:\...`, không text phía trước, dùng backslash).
  4. TUYỆT ĐỐI KHÔNG gửi ảnh suông rồi hỏi user màn gì khi chính agent chưa đọc ảnh.
- Thử nghiệm handler mới theo chu trình: Viết script thử nghiệm cô lập / test -> Chạy kiểm tra qua màn -> Nếu qua thành công mới lưu vào canonical script, nếu fail phải revert ngay.
