# Bẫy Thực Thi Popup Checkpoint và Navigation Confirm Trong Feed Swipe

## 1. Bẫy Blind Popup Checkpoint False Action (`if not actions:`)
Trong hàm `_maybe_run_gemphonefarm_blind_popup_checkpoint` (`feed_swipe_smoke.py`):
- Khi một rule (ví dụ `learn_more_dialog_dismiss`) có `detector_xpath` bắt trúng chữ *"Tìm hiểu thêm"* trên video quảng cáo nền, hàm `_gem_blind_action` cố gắng tìm nút Đóng (`action_xpath`).
- Nếu nút Đóng chưa xuất hiện hoặc không tìm thấy, `_gem_blind_action` trả về `(False, None, reason)`.
- Hàm append action thất bại vào danh sách: `actions.append({"rule": ..., "success": False, ...})`.
- **Bẫy cũ:** Kiểm tra `if not actions: return row`. Vì `actions` chứa 1 phần tử (dù `success: False`), điều kiện không thỏa mãn. Script tưởng rằng đã thực hiện hành động nên tiến hành chụp lại màn hình (`_capture_step`).
- Màn hình chụp lại bị phân loại thành `manual-needed:popup` và clobber trạng thái của `row`, làm dừng ca nuôi nick sớm.
- **Quy chuẩn sửa đổi:** BẮT BUỘC kiểm tra `if not any(action.get("success") for action in actions): return row`. Chỉ khi có ít nhất một hành động tap thành công trên thiết bị mới chụp lại màn hình.

## 2. Bẫy Navigation Confirm Popup Khi Chuyển Tab
Trong luồng chuyển tab Feed (`switch_friends` / `switch_following`):
- Sau khi tap tab và gọi blind checkpoint, nếu màn hình rơi vào popup promo overlay (như `feature_promo_overlay` có 2 nút "Tìm hiểu thêm" + "Đóng"):
- Nếu không có bước dismiss sau checkpoint, `confirm["status"]` giữ nguyên `manual-needed:popup`.
- Điều kiện `navigation_confirmed = confirm["status"] in {SUCCESS, DEGRADED}` bị fail.
- Script thoát ca nuôi ngay lập tức thay vì dọn popup để tiếp tục.
- **Quy chuẩn sửa đổi:** Bổ sung nhịp kiểm tra và gọi `_maybe_dismiss_navigation_confirm_popup` ngay sau checkpoint nếu `confirm` bị phát hiện là popup lành tính.
