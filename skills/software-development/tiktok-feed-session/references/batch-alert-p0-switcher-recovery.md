# Batch Alert P0: Switcher Missing & Account Lost Recovery Protocol

## Hiện tượng & Nhận diện
- Khi nhận batch alert: `⚠️ [P0 CẢNH BÁO MẤT PHIÊN / VĂNG ACCOUNT]` với lý do `manual-needed:account-switcher-missing-expected: expected account not found in account switcher`.
- Đây là lỗi do tài khoản chỉ định trong ca (slot N) không xuất hiện trên giao diện bottom-sheet switcher của app TikTok.

## Vai trò Coordinator (Session chính)
1. **O(1) Inspect:** Chạy `python D:/Taadaa/tools/inspect_machine.py <N>` để đọc model, pin, trạng thái màn hình và current focus.
2. **Đối chiếu dữ liệu:** 
   - Workbook `taikhoan_run_safe.xlsx` (hoặc `taikhoan_dat_v2_updated .xlsx`) kiểm tra tài khoản slot N.
   - Database `D:/Taadaa/data/tiktok_tracker.db` (bảng `farm_account_info` & `snapshots`) kiểm tra username, status LIVE/DIE và mapping hiện hành.
3. **Tuyệt đối cấm:** Tự viết script probe, test hàm hay can thiệp ADB trực tiếp trên máy ở session coordinator.

## Vai trò Worker Subagent (Qua delegate_task)
1. Bọc thiết bị bằng `DeviceContext(serial=..., machine=..., project='...', user_authorized=True)` để ngăn cronjob chiếm lock.
2. Sử dụng `atx-agent` (port 7912) làm cơ chế PRIMARY đọc XML hierarchy của Switcher sheet.
3. Chụp ảnh screencap thực tế lưu ra `D:/Taadaa/reports/` và gửi kèm `MEDIA:` trước khi đóng switcher hoặc teardown.
4. Đối chiếu xem nick bị thiếu thực tế trong app, hay bị lệch tên đăng nhập, hay bị văng phiên đăng nhập.
5. Teardown sạch sẽ: `am force-stop` và `input keyevent KEYCODE_HOME` sau khi đã có ảnh nghiệm thu.
