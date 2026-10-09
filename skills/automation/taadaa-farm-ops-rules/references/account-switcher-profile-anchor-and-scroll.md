# Pitfall: Account Switcher Anchor Misidentification & 8-Nick Scroll Viewport

## 1. Ngữ cảnh & Triệu chứng
- Khi chạy quy trình chuyển đổi tài khoản TikTok trên farm nhiều nick (tối đa 8 nick/máy), runner báo lỗi `ACCOUNT_SWITCHER_FAILED: select account failed: ACCOUNT_MISSING: expected account was not found`.
- **Nguyên nhân gốc rễ**:
  1. **Lệch Anchor Profile**: Header profile xuất hiện các icon mới như "Số lượt xem hồ sơ", prompt "Tám chuyện nào" / "Thì thầm to nhỏ". Khi tìm anchor mở switcher, runner nhận nhầm các element này hoặc tap nhầm vào top header bar `(539, 140)` gây mở full composer Nhật ký ("Bài đăng Thường nhật") thay vì bung bottom sheet switcher.
  2. **Tràn viewport (Off-screen)**: Bottom sheet switcher chỉ hiển thị 4 nick đầu trên Galaxy S7 (1080x1920). Nick thứ 5–8 bị khuất bên dưới nếu không vuốt cuộn (scroll).

## 2. Giải pháp chuẩn hóa

### A. Loại trừ Header Controls trong `account_switcher.py`
Trong `_PROFILE_HEADER_CONTROL_MARKERS`, bắt buộc thêm các control markers để không coi chúng là switcher anchor:
```python
_PROFILE_HEADER_CONTROL_MARKERS = frozenset(
    {
        "home", "for you", "following", "friends", "profile", "hồ sơ", "search", "menu", "more",
        "back", "close", "đóng", "thông báo", "notifications", "bell", "activity log", "nhật ký",
        "số lượt xem hồ sơ", "profile views", "lượt xem hồ sơ", "tám chuyện nào", "tám chuyện",
        "thì thầm to nhỏ",
    }
)
```

### B. Vị trí Tap mở Switcher trên Samsung S7 (1080x1920)
- Tọa độ kích hoạt switcher dropdown chuẩn trên giao diện Profile là vùng tên người dùng / display name: `(540, 552)`.
- Không tap `(539, 140)` nếu thanh header đang bị prompt Story chiếm dụng (sẽ mở composer Nhật ký).
- Thoát khỏi composer Story/Nhật ký nếu bị kẹt: Tap nút X tại `(84, 150)`.

### C. Cơ chế tự động vuốt cuộn (Scroll Fallback) khi thiếu tài khoản
Trong `select_exact_account`:
- Khi bắt được `AccountSwitcherError("ACCOUNT_MISSING")`:
  - Vuốt màn hình từ 80% chiều cao lên 50% chiều cao (`input swipe <x> <0.8*h> <x> <0.5*h> 450`).
  - Chờ tối thiểu 1.0s cho animation dừng hẳn.
  - Dump lại XML và retry tìm kiếm (tối đa 3 lần swipe).
  - Adapter phải cài đặt method `swipe(start_x, start_y, end_x, end_y, duration_ms)` qua ADB.
