# Follow Friends Suggestion Popup / In-Feed Card Triage (Case 57)

## 1. Triệu chứng & Hiện tượng
- Máy dừng phiên tại bước đối soát cuối ca với lý do: `profile verification mismatch: profile account mismatch` (ví dụ Máy 8 với nick `tolmavhj12k`).
- Ảnh hiện trường Farm Alerts cho thấy màn hình đang ở tab Hồ sơ, nhưng bị một modal dialog dạng popup che khuất: **"Follow bạn bè của bạn"** / **"Follow your friends"** chứa danh sách tài khoản gợi ý cùng các nút **"Follow lại"** và nút đóng `✕` ở góc trên bên phải.
- Do modal che mất phần header profile nơi chứa username `@handle`, parser trích xuất identity không đọc được username và báo mismatch.

---

## 2. Nguyên nhân (Anti-Pattern)
1. Thao tác điều hướng vào tab Hồ sơ kích hoạt popup gợi ý bạn bè từ danh bạ/tài khoản liên quan.
2. Nếu bộ xử lý popup chỉ ưu tiên nút "Không quan tâm" hoặc nút đóng `✕` mà không hỗ trợ nút "Follow lại", popup có thể bị bỏ lọt hoặc parser không nhận diện đúng cấu trúc nút Follow trên modal.
3. Nếu không có cơ chế 2 bước (pre_action tap Follow rồi mới tap Close `✕`), modal không được dọn sạch trước khi đọc username profile.

---

## 3. Giải pháp chuẩn 2 tầng (Core + Consumer)
1. **Tầng Core (`automation_core.tiktok.benign_popup` & `startup`):**
   - Phân loại `contact_follow_suggestion` bao phủ cả thẻ in-feed lẫn modal dialog.
   - Thẻ in-feed: tap trực tiếp nút `"Follow lại"` (`action="tap_follow_back"`).
   - Modal dialog: thiết lập `pre_action="tap_follow_button"` để tap Follow 1–2 tài khoản trong danh sách (dưới toạ độ tiêu đề, loại trừ nhãn `"Đã follow"` / `"Following"`), sau đó tap nút `✕` (`action="tap_follow_back_and_close"`). Nếu hết nút follow, fallback sang `action="dismiss_close_x"`.
   - `dismiss_tiktok_popups` xử lý chu trình pre_action: tap follow $\rightarrow$ recapture XML $\rightarrow$ tap close $\rightarrow$ verify sạch màn hình.
2. **Tầng Consumer (`feed_swipe_smoke.py`):**
   - Trong `_verify_profile_after_session`, kiểm tra và chủ động giải phóng popup trước khi trích xuất profile username.
   - Sau khi dismiss popup thành công, recapture XML tươi (`verify_profile_post_popup`) để đối soát username chính xác.
