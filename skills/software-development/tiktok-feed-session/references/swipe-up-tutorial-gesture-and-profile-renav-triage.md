# Swipe-Up Tutorial Gesture Overlay & Profile Navigation/Account Switcher Recovery (Case 56)

## 1. Hiện tượng & Bối cảnh (Sự cố Máy 56 — 31/08/2026)
- Máy 56 dừng phiên với lỗi `manual-needed:account-switcher-not-open: screen after re-navigation is not profile root` và giữ nguyên hiện trường.
- Trên giao diện TikTok For You xuất hiện overlay hướng dẫn cử chỉ vuốt lần đầu / tutorial gesture (`tv_strengthen_swipe_up_guide` với text "Vuốt lên để xem thêm" / "Swipe up to see more").

## 2. Phân tích nguyên nhân gốc (Root Cause)
1. **Overlay đánh chặn sự kiện chạm (Touch Interception):** Overlay `tv_strengthen_swipe_up_guide` nằm đè lên bề mặt video và thanh điều hướng đáy (Bottom Bar). Khi `_navigate_profile_for_preflight` tap vào nút "Hồ sơ", sự kiện chạm bị overlay chặn lại và không kích hoạt điều hướng sang tab Profile.
2. **Drift về Feed và Miss Profile Root:** Khi flow bấm phím BACK hoặc chuyển tài khoản bị trôi về Feed, re-navigation thất bại do overlay vẫn hiển thị → kiểm tra `_is_profile_root_screen` trả về False → flow fail-closed dừng phiên.
3. **Thiếu Handler trong Benign Popup Registry:** Hệ thống chưa đăng ký handler nhận diện và giải phóng tutorial cử chỉ vuốt này trong `BENIGN_POPUP_REGISTRY`.

## 3. Quy tắc & Giải pháp chuẩn
1. **Đăng ký `swipe_up_tutorial_overlay` vào Registry (Priority 89):**
   - **Detector:** Khớp resource-id `tv_strengthen_swipe_up_guide`, `swipe_up_guide` hoặc các cụm từ "vuốt lên để xem thêm", "swipe up to see more", "swipe up for more" thuộc package TikTok mục tiêu.
   - **Dismisser:** Thực hiện thao tác vuốt dọc tính theo tỷ lệ màn hình động (từ ~70% chiều cao lên ~20% chiều cao) để hoàn thành tutorial cử chỉ vuốt và giải phóng màn hình.
   - **Postcondition Verification:** Sau khi swipe, kiểm tra lại XML hoặc hierarchy để xác nhận overlay đã thực sự biến mất (`popup_closed=True/False`).
2. **Gia cố Navigation Target trong `calibrate_screens.py`:**
   - Trước khi thực hiện tap điều hướng (`tap_navigation_target`), kiểm tra xem màn hình có đang bị che bởi overlay/popup lành tính không (`find_matching_handler`). Nếu có, xóa điểm tap cũ (`point = None`), gọi dismisser giải phóng màn hình và recapture lại XML trước khi tap.
3. **Re-navigation 2 tầng trong `feed_swipe_smoke.py` (`_capture_profile_switcher_xml_with_add_phone_guard`):**
   - Nếu màn hình sau khi re-navigate Profile chưa phải là Profile root, kiểm tra allowlist handler lành tính (tutorial, location, v.v.), giải phóng an toàn và thực hiện re-navigate lần 2.
