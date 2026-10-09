# Targeted Canary CLI (--canary-hook) & TARGETED-CANARY-GATE

## Bối cảnh & Vấn đề
Khi debug hoặc sửa selector UI, điều hướng trang (search, tab Đã follow, profile anchor, nút follow), việc chạy toàn bộ phiên follow (end-to-end follow runner) hoặc chạy cả ca feed-session đem lại nhiều rủi ro:
1. **Lãng phí thời gian**: Chạy full session mất từ 5 đến 15 phút chỉ để kiểm tra 1 selector (như tab "Đã follow" hay ô Search).
2. **Tiêu tốn hạn mức & Rủi ro tài khoản**: Thực hiện follow thật trên nick nuôi có thể gây nhả follow, dính cooldown, hoặc đốt quota follow trong ngày.
3. **Thiếu bằng chứng cô lập**: Khó trích xuất screencap chính xác tại thời điểm selector được kích hoạt.

Do đó, kiến trúc yêu cầu chuẩn hóa **Targeted Canary CLI (`--canary-hook`)** và khóa cứng quy tắc **`TARGETED-CANARY-GATE`** vào `PROJECT_RULES.md`.

---

## 1. Đặc tả Targeted Canary CLI (`run_follow.py`)

### Tham số CLI
- `--canary-hook {open_following_tab,nav_search,verify_profile,single_follow}`: Chỉ định chính xác hook đơn lẻ cần chạy test.
- `--canary-target <UID>`: Target UID cần thực hiện thao tác (ví dụ anchor UID hoặc follower UID).
- `--canary-screencap <PATH>`: Đường dẫn lưu ảnh chụp màn hình sau khi hook hoàn tất để làm bằng chứng (UI evidence).

### Các Hook được hỗ trợ
1. **`open_following_tab`**:
   - Gọi `_open_following_tab(engine, uid, reason_holder)`.
   - Kiểm tra điều hướng search UID -> vào profile -> bấm tab "Đã follow" (Following).
2. **`nav_search`**:
   - Gọi `_nav_search(engine, uid)`.
   - Kiểm tra điều hướng search UID -> vào trang kết quả người dùng.
3. **`verify_profile`**:
   - Kiểm tra việc verify profile handle / identity.
4. **`single_follow`**:
   - Thực hiện follow 1 UID duy nhất và kiểm tra trạng thái nút follow / verify.

### Luồng thực thi an toàn trong `main()`
- Kiểm tra các cờ preflight (Device Lock, VPN nếu cần).
- Khởi tạo `FollowEngine` và `FollowAdapter`.
- Gọi hook tương ứng với target UID trong phạm vi giới hạn thời gian (timeout < 60s).
- Nếu có `--canary-screencap`, gọi `adapter.screencap(args.canary_screencap)` để xuất UI evidence.
- Trả về payload `FOLLOW_RESULT` dạng JSON với status `OK` hoặc `FAIL`, exit code phản ánh kết quả hook.

---

## 2. Quy tắc TARGETED-CANARY-GATE (Khóa vào PROJECT_RULES.md)

Khi sửa đổi selector hoặc luồng UI trong `tiktok-follow` và `tiktok-luot nuoi acc`:
1. **Không chạy blind full session**: CẤM chạy full follow session khi chỉ cần verify một thao tác UI/selector cụ thể.
2. **Bắt buộc dùng `--canary-hook`**: Phải cô lập lỗi bằng `--canary-hook` tương ứng trên máy thực nghiệm (canary machine).
3. **Thu thập Screencap Evidence**: Luôn truyền `--canary-screencap` và kiểm tra ảnh screencap/XML sau khi chạy để làm bằng chứng nghiệm thu (fresh UI evidence).
4. **Thời lượng Bounded**: Quá trình canary hook phải kết thúc trong vòng tối đa 60 giây, đảm bảo an toàn cho device và không chiếm giữ lock lâu dài.
