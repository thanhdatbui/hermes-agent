# Chẩn đoán & Xử lý False Mismatch do Màn hình Profile bị Cuộn Khuất Header (@username)

## Hiện tượng (Sự cố Máy 67 - Multi-machine Feed Session)
- **Thông báo Telegram:** `🚨 [MÁY 67] DỪNG PHIÊN - Script: multi-machine-feed-session - Lý do: profile verification mismatch: profile account mismatch`.
- **Hiện trường chụp được:** App TikTok đang mở ở tab Hồ sơ (Profile), nhưng màn hình đang ở trạng thái **cuộn xuống danh sách / lưới video đã đăng**.
- Phần header lớn chứa avatar, chỉ số tài khoản và chuỗi `@username` (ví dụ `@.m.hn6`) bị trôi khỏi viewport và không có trong UI XML hierarchy.
- Trên thanh top bar chỉ hiển thị tên hiển thị (Display Name) bị thu gọn/cắt ngắn (ví dụ `🌽 Mỹ Hâ... ⑦`).

## Cơ chế lỗi
1. Hàm `_verify_profile_after_session()` điều hướng sang tab Profile và parse UI XML tìm node text bắt đầu bằng `@` hoặc khớp chính xác với `ctx.account`.
2. Do màn hình bị cuộn xuống phần video grid, parser XML chỉ thu được các text của tab và grid video, không tìm thấy `@username`.
3. Cơ chế retry `time.sleep(1.5)` chụp lại XML lần 2 chỉ là capture tĩnh, không thể phục hồi vị trí cuộn nếu không có tương tác đưa màn hình về đỉnh (scroll up hoặc re-tap tab Hồ sơ).
4. Kết quả: `matched = False` $\rightarrow$ flow trả về `ExitStatus.MANUAL_NEEDED` và kích hoạt dừng phiên giữ nguyên hiện trường.

## Quy chuẩn Xử lý & Khắc phục
- **Trong Automation / Code:**
  - Khi `_verify_profile_after_session()` phát hiện không tìm thấy node `@username` (hoặc match thất bại lần 1), trước khi kết luận mismatch:
    1. Thực hiện re-tap vào nút tab "Hồ sơ" (hoặc swipe down / scroll up nhẹ) để TikTok scroll về đỉnh trang Profile.
    2. Đợi 1.0s và dump lại XML để lấy đầy đủ header chứa `@username`.
- **Triage thủ công / Live ops:**
  - Nếu hiện trường hiển thị màn hình Profile đã cuộn xuống lưới video, kiểm tra Display Name / video đã đăng để xác nhận đúng nick; không vội coi đây là lỗi sai tài khoản hay khoá nick.
