# In-Flight Recovery, Telemetry Completeness & Headless Surgery Discipline

## 1. Thứ Tự Dọn Popup vs Tắt App (Chống Mất Hiện Trường)
- **CẤM TUYỆT ĐỐI force-stop app trước khi xử lý popup:**
  - Tắt app sẽ làm bay mất UI XML và cấu trúc modal dialog hiện trường.
  - Một số popup quan trọng chỉ hiện 1 lần duy nhất (Terms, xác thực tài khoản), tắt app mở lại sẽ làm lệch state vĩnh viễn.
  - Các popup hệ thống (SystemUI, Google Play Protect, SIM dialog) không biến mất khi tắt app.
- **Thứ tự chuẩn tại thiết bị:**
  1. Dump ngay UI XML + Screenshot O(1).
  2. Quét selector tìm nút đóng (`✕`, `Bỏ qua`, `Để sau`, `Hủy`, `Đóng`) để dismiss tại chỗ khi app vẫn đang mở.
  3. Chỉ kích hoạt `force-stop` khi màn hình đơ cảm ứng hoàn toàn, ANR hoặc đen ngòm.

## 2. Kỷ Luật Vá Nóng (No In-Flight Screen Hanging)
- **CẤM bắt thiết bị treo màn hình chờ LLM vá code:**
  - Vòng lặp phẫu thuật chuẩn (Planner -> Worker O(1) <= 30 dòng -> Focused Test -> Canary -> Closeout Gate >= 85đ) mất từ 2-4 phút.
  - Thiết bị ngâm màn hình > 60s sẽ bị session timeout, quá nhiệt hoặc bị watchdog khác kill.
- **Quy trình chuẩn Zero-Touch:**
  1. Thiết bị dump `incident_envelope.json` (XML, ảnh, stacktrace, anchor).
  2. Trả thiết bị về Home ngay lập tức để bảo vệ tài khoản và nhả device-lock.
  3. Đẩy ticket vào hàng đợi cho Headless Incident Worker chạy ngầm phẫu thuật độc lập.

## 3. Telemetry Completeness Gate (Chống Sửa Mò)
- Khi nhận incident/report, kiểm tra tính đầy đủ của dữ liệu:
  `completeness_score = (có XML đọc được) + (có ảnh chụp hiện trường)`.
- **Nếu thiếu dữ liệu:**
  - CẤM TUYỆT ĐỐI gọi LLM sửa code nghiệp vụ (chống hallucination).
  - Tự động tạo Meta-Incident: Vá khối `except` của chính watchdog script đó để bổ sung lệnh dump XML và chụp màn hình.
  - Meta-Incident cũng bắt buộc đi qua toàn bộ 5 Cổng an toàn (Planner -> Worker <= 30 dòng -> Regression -> Canary -> Closeout >= 85đ).

## 4. Báo Cáo Sự Cố & Phân Nhóm Script
- **Gửi ngay sau khi fix xong:** Mỗi watchdog có chu kỳ riêng (theo ca, 6h/lần). Khi incident được xử lý xong và Closeout Gate thông qua, bắn ngay báo cáo kèm thẻ `MEDIA:<canary_image>` về đúng nhóm Telegram của repo.
- **Báo cáo định kỳ phân nhóm:** Tách biệt rõ ràng theo từng nhóm nghiệp vụ (Nuôi acc, Hotmail/Pass, 2FA TikTok, Chuẩn hoá Profile), không gộp chung một khối gây nặng mắt.
