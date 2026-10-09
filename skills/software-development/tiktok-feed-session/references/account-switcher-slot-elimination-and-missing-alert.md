# Quy tắc xử lý Account Switcher: Display Name, Slot Elimination & Cơ chế Chặn Login Tự Động trong Ca Nuôi

## 1. Hiện tượng Display Name trên Account Switcher
- **Bản chất**: Tài khoản TikTok đăng ký qua Gmail/Email thường có Tên hiển thị (Display Name) tự động sinh từ họ tên tài khoản Google (ví dụ `Trang Le`, `Hong Vu`, `Anh Pham`).
- **Hành vi UI TikTok**: Khi mở Account Switcher (popup chuyển tài khoản), TikTok ưu tiên hiển thị Display Name thay vì Handle ID (`@thu.trangg584`, `@hng.th.v713`, `@ngc.anh.phm33`).
- **Lỗi hệ thống cũ**: Bộ so khớp `_find_account_switch_option` chỉ so khớp chuỗi Handle ID, không nhận diện được Display Name nên đánh nhầm `ACCOUNT_MISSING` / `account-switcher-missing-expected`, làm dừng máy oan.

## 2. Thuật toán Loại trừ 8 Slot (Slot Elimination)
- Mỗi máy farm cố định tối đa 8 tài khoản tương ứng với 8 ca nuôi (`Tik1` -> `Tik8`).
- Khi Handle ID không khớp trực tiếp và không có placeholder `user\d+`:
  1. Trích xuất danh sách tài khoản đã biết của các ca khác trên máy (`known_other_accounts`).
  2. Lọc bỏ các phần tử hệ thống (`_NON_ACCOUNT_MARKERS`: Đóng, Thêm tài khoản, Chuyển đổi tài khoản).
  3. Loại trừ các nút trùng với các nick đã biết của 7 ca kia (`matches_switcher_identity`).
  4. Nút duy nhất còn lại chưa xác định chính là slot mục tiêu của ca hiện tại.
  5. Runner tự động chọn nút này, vào Profile đối soát ID và ghi log telemetry `strategy="slot_elimination"`.
- **Lợi ích**: Không cần bảo trì thêm cột Display Name trong bảng tính Excel.

## 3. Tại sao ca nuôi (Feed Session) KHÔNG tự động chạy Full-Login khi thiếu Nick?
- **Nguyên nhân**:
  1. **Ca nuôi là Fast-switching**, chỉ chuyển qua lại giữa các phiên đăng nhập sẵn có.
  2. **Tránh kẹt Captcha & OTP**: Luồng đăng nhập mới kích hoạt Slider Captcha ghép hình và mã xác minh OTP (Email/SMS), làm treo máy 10-15 phút và làm lệch nhịp điều phối 80 máy.
  3. **Bảo vệ an toàn cho 7 nick còn lại**: Thao tác cố login mới trên máy đang chạy feed dễ kích hoạt cờ kiểm tra thiết bị nghi vấn (Device Suspect) từ TikTok, gây nguy cơ bị **văng phiên hoặc checkpoint liên đới toàn bộ 7 nick đang sống trên máy**.
- **Chính sách**: Luồng nuôi áp dụng Fail-closed `manual-needed:account-switcher-missing-expected` để kỹ thuật viên chủ động nạp lại nick trong ca Login/Reconcile độc lập có proxy xoay và hạ tầng giải OTP riêng biệt.

## 4. Cơ chế Farm Alert tức thì (Bypass Batch Suppression)
- Trong `automation-core/src/automation_core/alerts.py`:
  - Phát hiện các từ khóa thiếu tài khoản (`account-switcher-missing-expected`, `account_missing`, `account-missing`, `thiếu nick`, `mất nick`, `account missing`).
  - Lập tức **Bypass** `_should_suppress_immediate_machine_alert()` để gửi Farm Alert Banner Đỏ khẩn cấp kèm ảnh màn hình hiện trường về nhóm Telegram kỹ thuật thay vì bị nuốt chờ gom batch.
