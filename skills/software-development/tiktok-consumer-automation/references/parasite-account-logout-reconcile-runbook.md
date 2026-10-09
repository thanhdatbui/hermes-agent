# Quy trình Logout Nick Ký Sinh (Parasite Reconcile) & Single-Machine Runbook

## Mục đích
Khi một thiết bị trên farm (ví dụ Samsung Galaxy S7) dính nick ký sinh (parasite account không thuộc pool quản lý, hoặc acc rác chiếm slot tài khoản thứ 8 khiến app không thể "Thêm tài khoản"), cần đăng xuất nick này và giải phóng slot.

## Công cụ chuẩn sẵn có trên Farm
Repo và script chuẩn:
- `D:/Taadaa/tools/watchdog_idle_parasite_reconcile.py`: Chứa hàm `do_logout(machine_id, username, serial)` chuẩn hóa flow TikTok UI.
- Hỗ trợ CLI param: `--machine <id>` (chỉ chạy duy nhất 1 máy).
- Hoặc script một lần: `D:/Taadaa/tools/clean_m76_m32.py`.

## Flow chuẩn các bước thao tác (UI Sequences)
1. **Kiểm tra Lock & Preflight**:
   - Check file lock `~/.codex/device-locks/machine_<ID>.lock.json` và `serial_<SERIAL>.lock.json`. Nếu không có lock, máy rảnh.
   - Wake & Unlock screen: `input keyevent 224` -> `input keyevent 82`.
2. **Vào Account Switcher**:
   - Mở app: `monkey -p com.ss.android.ugc.trill -c android.intent.category.LAUNCHER 1` hoặc `reg.open_app(serial)`.
   - Vào tab Profile: tap (972, 1857).
   - Mở Switcher: vuốt nhẹ profile bung sticky header `swipe 540 1100 540 600 250` rồi tap dropdown chevron (500, 140) hoặc dùng `reg.open_account_dropdown(serial)`.
3. **Switch sang nick ký sinh**:
   - Tìm username mục tiêu trong UI XML (text / content-desc) để lấy bounds, hoặc OCR.
   - Tap vào account để chuyển phiên. Chờ 6-8s, bấm Back (`keyevent 4`) nếu có popup story / keyboard.
4. **Thực hiện Logout trong Cài đặt**:
   - Vào Profile (972, 1857).
   - Mở menu 3 gạch (1005, 150).
   - Tap "Cài đặt và quyền riêng tư" (thường ở đáy menu hoặc khoảng Y: 1102 - 1250).
   - Cuộn 6 lần xuống đáy trang Cài đặt: `swipe 540 1600 540 300 250`.
   - Tap nút "Đăng xuất" ở đáy màn hình (khoảng 300, 1640 hoặc 540, 1668).
   - Xác nhận "Đăng xuất" trên dialog đỏ (khoảng 540, 1640 - 1662).
5. **Nghiệm thu (Verification & Evidence Gate)**:
   - Mở lại Profile và Account Switcher.
   - Chụp ảnh màn hình lưu vào `D:/Taadaa/reports/m<ID>_switcher_verified_logout.png`.
   - Đảm bảo trong Switcher không còn nick ký sinh và xuất hiện lại dòng "Thêm tài khoản" / "Add account" (tổng số nick ≤ 7).
   - Trả ảnh qua cú pháp: `MEDIA:D:/Taadaa/reports/m<ID>_switcher_verified_logout.png` trên một dòng riêng.
6. **Teardown**:
   - `am force-stop com.ss.android.ugc.trill`
   - `input keyevent 3` (KEYCODE_HOME)

## Pitfall về Budget khi thao tác ADB
- **Cấm đọc code dàn trải**: Không đọc từng file utility lớn (`social_reg_v1.py`) khi đã có script `watchdog_idle_parasite_reconcile.py` hoặc script mẫu.
- **Thực thi trực tiếp**: Viết script ad-hoc hoặc invoke thẳng `do_logout` bằng python one-liner trong vòng 2-3 turn đầu tiên để dành budget cho việc chụp ảnh và nghiệm thu kết quả.
