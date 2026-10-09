# Benign Add Phone Popup Auto-Dismiss & Child Safety Override Guard (Case 112, 2026-09-05)

## 1. Hiện tượng & Triệu chứng lỗi (Máy 74)
- **Triệu chứng alert:** `benign Add phone popup detected; dismiss requires explicit flag; swipe recovery (2 swipes) still stuck`
- **Tác động:** Máy dừng phiên nuôi feed oan uổng dù popup "Thêm số điện thoại" (Add phone) là một popup onboarding lành tính có nút đóng [X] an toàn và không phải là challenge hay checkpoint nhạy cảm.

## 2. Root Cause Analysis
1. **Parent-Child Safety Override Trap (`multi_machine_feed_session.py`)**:
   - Trong `multi_machine_feed_session.py`, worker khởi tạo `child_safety["allow_benign_popup_dismiss"] = True` để kích hoạt tự động đóng các popup lành tính.
   - Tuy nhiên, ngay bên dưới có vòng lặp sao chép từ `parent_safety`:
     ```python
     for _key in ("allow_benign_popup_dismiss", ...):
         if _key in parent_safety:
             child_safety[_key] = parent_safety[_key]
     ```
   - Trong `config.example.yaml`, giá trị mặc định là `allow_benign_popup_dismiss: false`. Vòng lặp này đã ghi đè (overwrite) `child_safety["allow_benign_popup_dismiss"]` trở về `False`.
2. **Fail-closed Chặn Đóng Popup Lành Tính (`feed_swipe_smoke.py`)**:
   - Hàm `_maybe_dismiss_add_phone_row` kiểm tra:
     `if not ctx.config.get("safety", {}).get("allow_benign_popup_dismiss", False):`
   - Khi cờ là `False`, nó từ chối gọi `dismiss_add_phone_popup` và đánh dấu `safety_reason = "benign Add phone popup detected; dismiss requires explicit flag"`.
   - Luồng fallback kích hoạt `_swipe_recovery_on_stuck` (thử 2 lần vuốt feed qua ADB), nhưng modal dialog Add phone che trọn màn hình nên vuốt không tắt được dialog -> dừng phiên `manual-needed`.

## 3. Quy chuẩn Khắc phục (Case 112)
1. **Bảo vệ cờ `child_safety` trong `multi_machine_feed_session.py`**:
   - Loại bỏ `allow_benign_popup_dismiss` khỏi danh sách sao chép đè thô từ `parent_safety`.
   - Chỉ override nếu parent explicitly set `True`:
     ```python
     if parent_safety.get("allow_benign_popup_dismiss") is True:
         child_safety["allow_benign_popup_dismiss"] = True
     ```
2. **Mặc định cho phép dismiss popup lành tính Add Phone trong `feed_swipe_smoke.py`**:
   - Thay đổi kiểm tra sang:
     ```python
     allow_dismiss = ctx.config.get("safety", {}).get("allow_benign_popup_dismiss", True)
     if not allow_dismiss:
         ...
     ```
   - Cho phép tự động đóng Add Phone popup qua nút [X] theo cơ chế an toàn, trừ khi có cấu hình cấm tường minh (`False`).
