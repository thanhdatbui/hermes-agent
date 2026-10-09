# Pitfall: Account Switcher Misidentifying Profile Controls & Long List Viewport

## 1. Ngữ cảnh & Triệu chứng
- **Hiện tượng**: Khi chạy upload TikTok trên thiết bị có nhiều nick (tối đa 8 nick), runner báo lỗi `ACCOUNT_SWITCHER_FAILED: select account failed: ACCOUNT_MISSING: expected account was not found`.
- **Nguyên nhân kép**:
  1. **Anchor Header sai lệch**: Header profile xuất hiện các icon mới như "Số lượt xem hồ sơ", prompt "Tám chuyện nào" / "Thì thầm to nhỏ", hoặc "Tạo một Nhật ký" (Story composer). Khi tìm anchor mở switcher, runner nhận nhầm các element này hoặc tap nhầm vào vùng top header `(539, 140)` gây mở full màn hình compose Nhật ký thay vì bung bottom sheet switcher.
  2. **Tràn viewport (Off-screen)**: Bottom sheet switcher chỉ hiển thị tối đa 4 nick trên viewport đầu tiên của màn hình 1080x1920 (Galaxy S7). Nick thứ 5-8 bị khuất hoàn toàn nếu không cuộn (scroll).

## 2. Giải pháp kỹ thuật chuẩn hóa

### A. Loại trừ Header Controls trong `account_switcher.py`
Trong `_PROFILE_HEADER_CONTROL_MARKERS`, bắt buộc có đầy đủ các control markers để không coi chúng là switcher anchor:
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
- Vị trí kích hoạt dropdown switcher chuẩn trên giao diện profile là vùng tên người dùng / display name: `(540, 552)`.
- Tuyệt đối không tap vào `(539, 140)` nếu thanh top header đang bị prompt Story chiếm dụng (sẽ mở composer "Bài đăng Thường nhật").
- Nếu lỡ rơi vào màn hình Story/Nhật ký: Tap nút X đóng tại `(84, 150)` để quay lại Profile root (lệnh `Back` đơn thuần không thoát được một số dạng composer overlay).

### C. Tự động vuốt cuộn (Scroll Fallback) khi thiếu tài khoản
Trong `select_exact_account`:
- Khi bắt được `AccountSwitcherError("ACCOUNT_MISSING")`:
  - Vuốt màn hình từ 80% chiều cao lên 50% chiều cao (`input swipe <x> <0.8*h> <x> <0.5*h> 450`).
  - Chờ tối thiểu 1.0s cho animation trượt dừng hẳn.
  - Dump lại XML và retry tìm kiếm tài khoản mục tiêu (tối đa 3 lần swipe).
  - Yêu cầu adapter phải cài đặt method `swipe(start_x, start_y, end_x, end_y, duration_ms)` thông qua `adb shell input swipe`.

## 3. Quy trình chốt phiên (Closeout Gate) cho repo `automation-core`
- Bắt buộc chạy thẩm định trước khi push:
  `python D:/Taadaa/tools/closeout_gate.py --repo D:/Taadaa/automation-core --base HEAD~1 --json-output`
- Chỉ push khi Sol Auditor chấm `APPROVED` (Điểm >= 85/100).
