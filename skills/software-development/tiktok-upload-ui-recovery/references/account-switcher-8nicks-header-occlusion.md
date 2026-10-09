# Account Switcher 8 Nicks & Header Anchor Occlusion Pitfalls

## 1. Hiện tượng Tràn Viewport Switcher Bottom Sheet (8 Tài Khoản)
- **Triệu chứng**: Gặp lỗi `[ACCOUNT_SWITCHER_FAILED] select account failed: ACCOUNT_MISSING: expected account was not found`.
- **Bản chất**: Trên màn hình tỉ lệ 16:9 / 1080x1920 (như Samsung Galaxy S7), bottom sheet chỉ hiển thị ~4 tài khoản đầu tiên. Với các máy nạp đủ 8 nick farm (Tik1 - Tik8), các tài khoản từ vị trí thứ 5 đến thứ 8 nằm hoàn toàn ngoài viewport (off-screen).
- **Giải pháp**:
  - Không ném lỗi ngay khi `ACCOUNT_MISSING`.
  - Thực hiện vuốt cuộn (`swipe` từ `start_y = int(height * 0.80)` lên `end_y = int(height * 0.50)` với duration 450ms).
  - Đặt thời gian settle `>= 1.0s` để danh sách dừng chuyển động hoàn toàn trước khi dump lại XML.
  - Cho phép lặp lại tối đa 3 lần cuộn trước khi kết luận thiếu tài khoản.

## 2. False Profile Anchor do Icon/Button Trên Profile Header
- **Triệu chứng**: `open_switcher` báo thành công (`Switcher opened via core ✓`) nhưng thực tế mở ra trang khác (như trang Lịch sử xem hồ sơ / Xem tin / Giao diện tính năng mới) khiến XML không chứa danh sách nick switcher hoặc chứa node của tính năng lạ.
- **Bản chất**:
  - Khi không tìm thấy semantic anchor với username/display name khớp identity, logic `find_switcher_anchor` kích hoạt fallback `allow_generic_header=True`.
  - Trên TikTok xuất hiện các nút/icon như "Số lượt xem hồ sơ" (`com.ss.android.ugc.trill:id/img`, `content-desc='Số lượt xem hồ sơ'`), "Tám chuyện nào", "Profile views".
  - Do các button này nằm ở header top (`y <= generic_header_y`) và có bounds hợp lệ, chúng bị nhặt nhầm thành candidate duy nhất và bị tap nhầm thay vì mở menu switcher.
- **Giải pháp**:
  - Bổ sung triệt để các chuỗi nhận diện vào `_PROFILE_HEADER_CONTROL_MARKERS` trong `automation-core/src/automation_core/tiktok/account_switcher.py`:
    ```python
    _PROFILE_HEADER_CONTROL_MARKERS = frozenset(
        {
            "home", "for you", "following", "friends", "profile", "hồ sơ", "search", "menu", "more",
            "back", "close", "đóng", "thông báo", "notifications", "bell", "activity log", "nhật ký",
            "số lượt xem hồ sơ", "profile views", "lượt xem hồ sơ", "tám chuyện nào", "tám chuyện",
        }
    )
    ```
  - Khi không có candidate hợp lệ, fallback tap theo tọa độ cố định của header profile (tỉ lệ `(sw // 2, int(sh * 150 / 1920))`) để mở dropdown switcher an toàn.
