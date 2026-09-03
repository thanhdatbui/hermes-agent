# Quy Chuẩn XML-First Cho Toàn Bộ Popup / Navigation / AI Recovery (2026-08-21)

## 1. Nguyên Tắc Cốt Lõi: XML-First Element Bounds
- **Loại bỏ 100% tọa độ cứng:** Tuyệt đối không hardcode `ctx.tap(x, y)` hay `input tap x y` cố định trong các hàm xử lý popup và navigation.
- **Dùng Element Bounds:** Luôn parse cây ATX XML (`parse_xml`, `iter_elements`, `find_element`), tìm đúng Node UI theo `text`, `content-desc`, hoặc `resource-id`, rồi tính tâm bounds:
  ```python
  cx = (bounds[0] + bounds[2]) // 2
  cy = (bounds[1] + bounds[3]) // 2
  ctx.tap(cx, cy)
  ```
- **Fail-Closed & Không Tap Mù:** Nếu không tìm thấy Node UI mục tiêu trong XML:
  - Với Modal Popup: Trả về `dismissed=False` (NO-OP), tuyệt đối không tap fallback tọa độ mù.
  - Với Màn hình Fullscreen (Camera, LIVE, WebView): Gửi phím `KEYCODE_BACK` có hậu kiểm trạng thái màn hình thay đổi.

## 2. Policy Firewall Cho AI Auto-Recovery (`safe_executor.py`)
- **Strict Leaf Node Validation:** Khi AI sinh lệnh tap tọa độ, bắt buộc đối soát tọa độ với XML snapshot tươi. Tọa độ phải nằm trong một leaf node hợp lệ (có metadata hoặc `clickable=true`). Loại bỏ hoàn toàn root/fullscreen container `[0,0][1080,1920]` (> 85% diện tích màn hình).
- **Chặn Tap Trên Quảng Cáo:** Khi màn hình là Quảng cáo / Khảo sát (`ad`, `survey`, `sponsored`), Policy Firewall chặn tuyệt đối lệnh tap (bắt buộc lướt qua bằng `swipe`).
- **Fail-Closed Tuyệt Đối:** Nếu tọa độ không xác thực được qua XML, hệ thống hủy thao tác ngay (NO-OP), không tự ý chuyển thành phím `BACK`.

## 3. Cách Ly Tài Khoản Bị Đăng Xuất (Account Logged Out Quarantine)
- Khi phát hiện popup thông báo tài khoản bị đăng xuất (`dismiss_account_logged_out_popup`), bot lập tức kích hoạt cơ chế cách ly `quarantine_logged_out_account` và dừng phiên ngay lập tức (`dismissed=False`, `terminal=True`), tuyệt đối không tự ý bấm nút OK / Đăng nhập lại để bảo vệ tài khoản khỏi checkpoint.

## 4. Import Kép Cho CLI Agent (`agent.py`)
Khi tách module hoặc helper trong package con của `python_runner`, luôn bọc import để hỗ trợ cả 2 ngữ cảnh (pytest runner và subprocess standalone CLI):
```python
try:
    from .safe_executor import _execute_adb
except ImportError:
    from ai_recovery.safe_executor import _execute_adb
```
Tránh lỗi `ImportError: attempted relative import with no known parent package` khi agent được spawn độc lập bởi Telegram Alert.
