# Case 112: Tự Động Dismiss Benign Add Phone Popup Trong Feed Session & Bảo Vệ Cờ Child Safety

## 1. Hiện tượng & Sự cố thực tế (Alert Máy 74 - Nick ninhsyhez6u)
- **Triệu chứng:** Feed session dừng với trạng thái `manual-needed:add-phone` kèm lỗi:
  `benign Add phone popup detected; dismiss requires explicit flag; swipe recovery (2 swipes) still stuck`.
- **Hiện trường:** TikTok hiển thị popup modal yêu cầu thêm số điện thoại ("Add phone number to protect your account") kèm nút Close X ở góc trên.
- **Hậu quả:** 2 recovery swipes được kích hoạt nhưng thao tác vuốt màn hình không thể đóng được modal dialog của TikTok, khiến máy kẹt ở trạng thái manual-needed và dừng phiên chạy.

## 2. Nguyên nhân cốt lõi (Anti-Patterns)
1. **Ghi đè flag con ngoài ý muốn (`multi_machine_feed_session.py`):**
   Trong `_run_child`, `child_safety["allow_benign_popup_dismiss"] = True` được bật mặc định nhằm tự động đóng popup vô hại. Tuy nhiên ngay sau đó, một vòng lặp duyệt qua `parent_safety` đã copy đè giá trị `allow_benign_popup_dismiss: false` (từ `config.example.yaml`) vào `child_safety`, làm vô hiệu hóa thiết lập trước đó.
2. **Khóa dismiss mặc định trong helper (`feed_swipe_smoke.py`):**
   Hàm `_maybe_dismiss_add_phone_row` kiểm tra:
   `if not ctx.config.get("safety", {}).get("allow_benign_popup_dismiss", False):`
   Do giá trị fallback mặc định là `False`, khi config không truyền flag tường minh, hàm từ chối đóng popup và trả về `manual-needed`.

## 3. Quy tắc & Giải pháp chuẩn
1. **Fallback cho popup an toàn/vô hại (Benign Popups):**
   - Trong `_maybe_dismiss_add_phone_row`, chuyển fallback lấy cờ sang `True`:
     `allow_dismiss = ctx.config.get("safety", {}).get("allow_benign_popup_dismiss", True)`
     Popup Add phone là loại popup lành tính, có thể bấm nút X đóng an toàn để tiếp tục xem feed mà không ảnh hưởng tài khoản.
2. **Kế thừa safety config an toàn giữa parent và child:**
   - Không đưa các cờ đã được child gán mặc định an toàn (`allow_benign_popup_dismiss`) vào vòng lặp copy đè mù quáng từ `parent_safety`.
   - Chỉ cho phép `parent_safety` override nếu có chỉ định rõ ràng hoặc giữ an toàn tối đa cho child runner:
     ```python
     for _key in ("allow_blanket_dismiss", "allow_network_force_stop_recovery", "allow_device_reboot_recovery", "allow_prepare_tiktok", "allow_feed_swipe"):
         if _key in parent_safety:
             child_safety[_key] = parent_safety[_key]
     if parent_safety.get("allow_benign_popup_dismiss") is True:
         child_safety["allow_benign_popup_dismiss"] = True
     ```
3. **Unit Test Coverage:**
   - Mọi thay đổi logic dismiss popup phải có unit test kiểm thử cả 2 nhánh:
     - Branch 1: Config default -> Tự động dismiss thành công.
     - Branch 2: Explicit `allow_benign_popup_dismiss: False` -> Giữ nguyên safety guard, không tự dismiss.
