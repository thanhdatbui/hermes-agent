# Quy tắc vận hành Switcher Display Name, Thuật toán loại trừ Slot (Slot Elimination) & Cảnh báo Thiếu Tài khoản (Account Missing Alert)

## 1. Hiện tượng Display Name trên TikTok Account Switcher
- Khi tài khoản TikTok được đăng ký bằng Gmail/Email và chưa đổi nickname (chỉ có Display Name họ tên như `Trang Le`, `Hong Vu`, `Anh Pham`):
  - Giao diện Account Switcher của TikTok ưu tiên hiển thị Display Name thay vì Handle ID (`@thu.trangg584`, `@hng.th.v713`, `@ngc.anh.phm33`).
  - Nếu hệ thống chỉ so khớp exact string với Handle ID, matcher sẽ báo không tìm thấy (`ACCOUNT_MISSING` / `account-switcher-missing-expected`), dẫn tới dừng ca nuôi oan uổng.

## 2. Giải thuật loại trừ 8 Slot (Slot Elimination)
- Mỗi thiết bị farm được cố định tối đa 8 slot tương ứng với 8 ca nuôi (Tik1 -> Tik8).
- **Thuật toán**:
  1. Khi mở Switcher, kiểm tra khớp Handle ID trực tiếp hoặc pattern `user\d+`.
  2. Nếu không khớp bất kỳ Handle ID nào, trích xuất danh sách các tài khoản của các ca còn lại trên máy (`known_other_accounts`).
  3. Lọc bỏ các marker hệ thống (`_NON_ACCOUNT_MARKERS`: `Đóng`, `Thêm tài khoản`, `Chuyển đổi tài khoản`).
  4. Loại trừ các nút trùng với các nick đã biết của 7 ca kia.
  5. Nút duy nhất còn lại chưa xác định chính là slot của ca hiện tại (dù đang hiển thị Display Name bất kỳ).
  6. Runner tự động chọn nút này, vào Profile đối soát lại danh tính và ghi log telemetry `strategy="slot_elimination"`.
- **Lợi ích**: Farm hoàn toàn không cần kỹ thuật viên phải mở Excel để nhập thêm cột Display Name thủ công.

## 3. Bypass Batch Alert Suppression khi thực sự thiếu Nick vật lý
- **Quy tắc**: Lỗi thiếu tài khoản vật lý trên máy (ví dụ Máy 72 chỉ có 7 nick, thiếu hẳn nick thứ 8 `@m.ngc4624`) là lỗi chặn đứng vận hành của slot đó.
- Trong `automation-core/src/automation_core/alerts.py`:
  - Bắt buộc kiểm tra `is_account_missing` với các biến thể keyword: `account-switcher-missing-expected`, `account_missing`, `account-missing`, `thiếu nick`, `mất nick`, `account missing`.
  - Khi phát hiện, lập tức **BYPASS** cờ `_should_suppress_immediate_machine_alert()` để bắn Telegram Farm Alert Banner Đỏ ngay lập tức về nhóm kỹ thuật farm kèm ảnh màn hình hiện trường.

## 4. Tại sao ca nuôi (Feed Session) KHÔNG tự động đăng nhập khi thiếu Nick?
- **Nguyên nhân cốt lõi**: Ca nuôi là Fast-switching giữa các session đã login sẵn, không phải Onboarding.
- **Rủi ro khi tự động Full-Login giữa ca nuôi**:
  - Đăng nhập mới trên app TikTok kích hoạt Slider Captcha ghép hình và mã xác minh OTP (Email/SMS), làm treo máy 10-15 phút và lệch nhịp toàn farm.
  - Hành vi cố đăng nhập mới bất thường trên thiết bị đang chạy feed dễ kích hoạt cờ kiểm tra gian lận (Device Suspect), có nguy cơ làm **văng phiên hoặc checkpoint liên đới toàn bộ 7 nick còn lại đang sống trên máy**.
- **Chính sách an toàn**: Khi thiếu nick vật lý, runner bắt buộc phải **Fail-closed** dừng máy đó lại, phát Farm Alert để kỹ thuật viên farm chủ động nạp lại nick an toàn trong ca riêng (Batch Reconcile/Login có proxy xoay và IMAP OTP).
