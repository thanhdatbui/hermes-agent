# Account Switcher 7-8 Acc Safe Tap & Bottom-Row Recovery (2026-09-25)

## 1. Hiện Tượng & Triệu Chứng
- Trên Samsung S7 (1080x1920), khi app TikTok đã chứa từ 6 đến 8 tài khoản trong Account Switcher, danh sách tài khoản chiếm gần như toàn bộ chiều cao màn hình.
- Nút `"Thêm tài khoản"` (hoặc hàng tài khoản thứ 7/8) bị đẩy sát mép dưới cùng của bottom sheet, thường rơi vào vùng bounds:
  `[0, 1788][1080, 1920]`
- Logic tính tọa độ tâm mặc định:
  `x = (0 + 1080) // 2 = 540`
  `y = (1788 + 1920) // 2 = 1854`
- Tọa độ `y = 1854` nằm sát đáy màn hình, rơi thẳng vào vùng thanh điều hướng (Navigation Bar) hoặc khu vực cử chỉ của Android. Kết quả: cú tap bị Android chặn hoặc nuốt chửng, không kích hoạt được form đăng nhập mới, dẫn đến script bị timeout 300s.

## 2. Giải Pháp Safe-Point Tap (Upper 1/3 Row Bounds)
Thay vì tap vào tâm của row, tính điểm tap an toàn lệch lên 1/3 phía trên của bounds:
```python
x1, y1, x2, y2 = (int(v) for v in bounds_match.groups())
safe_x = (x1 + x2) // 2
safe_y = y1 + max(1, (y2 - y1) // 3)
```
- Với bounds `[0, 1788][1080, 1920]`:
  `safe_x = 540`
  `safe_y = 1788 + (1920 - 1788) // 3 = 1788 + 44 = 1832`
- Tọa độ `(540, 1832)` nằm chắc chắn bên trong phần thân của nút và hoàn toàn nằm ngoài vùng nhạy cảm của thanh điều hướng.

## 3. Cơ Chế Bỏ Qua Login Khi Nick Mục Tiêu Đã Nằm Trong Switcher
- Khi runner nuôi acc báo thiếu nick trong switcher (`ACCOUNT_NOT_IN_SWITCHER` / `session_lost`), có khả năng nick mục tiêu chưa mất phiên mà chỉ bị đẩy xuống cuối danh sách (row 7 hoặc 8).
- **Quy tắc bắt buộc trước khi bấm "Thêm tài khoản"**:
  1. Quét toàn bộ XML danh sách Switcher xem username mục tiêu có tồn tại hay không (kiểm tra cả `text` và `content-desc` trong các node của package `com.ss.android.ugc.trill`).
  2. Nếu tìm thấy username mục tiêu: Bấm thẳng vào row đó để chuyển tài khoản (switch account), sau đó xác minh profile post-switch.
  3. Tuyệt đối KHÔNG cố bấm "Thêm tài khoản" và chạy lại flow login khi tài khoản đã có sẵn phiên live trên máy.
