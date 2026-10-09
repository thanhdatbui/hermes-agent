# Account Switcher: Display Name vs Handle & Slot Elimination Pattern

## Hiện tượng thực tế (Farm 2026-09-19)
- Trên app TikTok của Android Phone Farm, một số tài khoản khi tạo bằng Gmail hoặc chưa đồng bộ/đổi nickname trong profile thì giao diện **Account Switcher** (Chuyển đổi tài khoản) sẽ hiển thị **Display Name** (Họ tên đăng ký mail, ví dụ `Trang Le`, `Hong Vu`, `Anh Pham`) thay vì `@username` (như `@thu.trangg584`, `@hng.th.v713`, `@ngc.anh.phm33`).
- Khi runner chỉ so khớp cứng theo username/handle:
  - Máy bị fail với stop reason: `manual-needed:account-switcher-missing-expected: expected account not found in account switcher`.
  - Bị đánh giá nhầm thành `ACCOUNT_MISSING` dù tài khoản vẫn đang đăng nhập hợp lệ trên thiết bị.

## Giải pháp: Thuật toán Loại trừ Slot (Slot Elimination)
Mỗi máy farm cố định tối đa 8 tài khoản tương ứng 8 ca (`Tik1` -> `Tik8`):
1. Lấy danh sách `known_other_accounts` (7 tài khoản của các ca khác trên cùng máy) từ context (`ctx.config.get("feed_source_accounts")`).
2. Quét toàn bộ nút tài khoản trong popup switcher XML.
3. Loại trừ các tài khoản đã trùng khớp với `known_other_accounts`.
4. Slot còn lại chưa xác định chính là slot của ca hiện tại (đang bị hiển thị dưới dạng Display Name).
5. Tap vào slot đó -> Vào trang profile -> Hàm verify profile sẽ đối soát cả username và display name để xác nhận hợp lệ và tiếp tục phiên nuôi nick.

## Quy tắc Gửi Farm Alert khi Thiếu Nick Thật
- Khi một máy thực sự bị thiếu nick (sau khi loại trừ mà switcher vẫn không có slot, như trường hợp máy chỉ có 7 nick thay vì 8):
  - Lỗi này là lỗi vật lý/vận hành, cần kỹ thuật viên đăng nhập lại nick lên máy.
  - **Bắt buộc bypass batch suppression**: Trong `automation_core.alerts.send_farm_machine_alert`, khi `error_reason` chứa các từ khóa (`account-switcher-missing-expected`, `account_missing`, `account-missing`, `thiếu nick`, `mất nick`, `account missing`), hệ thống KHÔNG được nuốt alert theo cơ chế batch aggregation mà phải gửi ngay Telegram message kèm Banner Đỏ về kênh Farm Alert.
