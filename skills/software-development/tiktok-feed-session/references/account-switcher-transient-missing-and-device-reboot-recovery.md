# Account Switcher Transient Missing & Device Reboot Recovery (2026-09-02)

## Bối cảnh & Hiện tượng (Incident Máy 10)
- Script `multi-machine-feed-session` dừng phiên báo lỗi:
  `manual-needed:account switcher requires manual review` trên tài khoản `laquyen2601`.
- Ảnh hiện trường tại thời điểm lỗi chỉ hiển thị duy nhất 1 nick `djricnvy2ez` và nút "+ Thêm tài khoản".
- Người dùng xác nhận đã đăng nhập đủ 6 nick từ hôm trước và thắc mắc tại sao lại bị mất session / văng nick liên tục.

## Bài học & Điều cấm kỵ chẩn đoán (Anti-Patterns)
1. **CẤM võ đoán nguyên nhân khi chưa có bằng chứng:**
   - Không đổ lỗi cho ViChanger (ViChanger chỉ là VPN và flow đã loại bỏ).
   - Không đổ lỗi cho mất kết nối 4G/proxy hay xoay IP làm văng nick khi mạng đã được định tuyến cứng qua WiFi/MikroTik.
   - Không đổ lỗi cho xung đột RAM hay trùng session ở máy khác khi chưa đối soát dữ liệu toàn farm (đã kiểm tra 458 nick trên toàn bộ Excel không có nick nào của máy bị trùng).

2. **Dấu hiệu máy tự khởi động lại (Device Reboot / Sụt áp USB):**
   - Khi máy bị sụt áp, lỏng cáp hoặc khởi động lại đột ngột (`uptime < 2 min`), app TikTok sau khi mở lại có thể chưa kịp load danh sách tài khoản từ cache SQLite, dẫn đến switcher tạm thời chỉ hiện nick đang active.
   - Kiểm tra `uptime` ngay khi thấy thiết bị chập chờn kết nối ADB: `adb -s <serial> shell uptime`.

## Quy trình Khôi phục & Xác minh Chuẩn

### Bước 1: Kiểm tra Uptime & Trạng thái thực trên app TikTok
- Kiểm tra `uptime` và kết nối WiFi/ADB.
- Mở TikTok, vào tab "Hồ sơ" và chạm header để mở bottom sheet "Chuyển đổi tài khoản" (`id/pmf`).
- Đọc hierarchy qua ATX dump (`/jsonrpc/0` method `dumpWindowHierarchy`) để liệt kê chính xác các nick thực sự đang có trên máy (thực tế máy 10 có đủ 5/6 nick: `laquyen2601`, `djricnvy2ez`, `tranvantrang9810`, `khoa50076`, `anhtruong840`).

### Bước 2: Dọn dẹp Stale Lock & Phục hồi ATX Agent
- Xóa stale device-lock file nếu tiến trình runner cũ đã chết:
  `rm -f ~/.codex/device-locks/machine_<M>.lock.json`
- Nếu `uiautomator dump` trả exit code 137 (atx-agent / uiautomator bị treo):
  `adb -s <serial> shell "pkill -9 -f atx-agent; am force-stop com.github.uiautomator; uiautomator quit"`
  Khởi động lại: `adb -s <serial> shell "/data/local/tmp/atx-agent server -d"`
  Forward port: `adb -s <serial> forward tcp:7912 tcp:7912`

### Bước 3: Đưa TikTok về màn hình Feed trước khi chạy Canary
- Nếu TikTok đang dừng ở màn hình Đăng nhập / Báo cáo sự cố / Trợ giúp đăng nhập, `feed-session-smoke` sẽ nhận diện `manual-needed:login` và dừng lại.
- Bấm Back (hoặc tap nút "Đóng" / tap tab "Trang chủ") để đưa TikTok về màn hình For You ("Đề xuất").

### Bước 4: Chạy Canary Feed Session Smoke
- Chạy lệnh focused canary:
  `python python_runner/run_tiktok.py --mode feed-session-smoke --device <serial> --machine <M> --account <username> --allow-navigation-only --allow-feed-swipe --allow-benign-popup-dismiss --max-swipes 2`
- Xác nhận `status: success`, hoàn thành đủ swipe và profile matched.
