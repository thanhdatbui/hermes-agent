# Follow Friends Suggestion Popup Handling & Spatial Safeguards (2026-08-25)

## 1. Bản chất Popup "Follow bạn bè của bạn"
- **Tiêu đề (Anchor):** `text="Follow bạn bè của bạn"` / `content-desc="Follow bạn bè của bạn"` (hoặc tiếng Anh: `"Follow your friends"`).
- **Nút bấm danh sách:**
  - Nút màu đỏ chữ trắng: text chính xác là **`Follow`** (class `android.widget.Button`, resource-id `com.ss.android.ugc.trill:id/thb`).
  - *Lưu ý quan trọng:* Chữ `"Follow lại"` thuộc về thẻ gợi ý bạn bè / follow back ở feed, còn popup modal này là nút chữ **`Follow`**.
- **Nút đóng (Close X):** `content-desc="Đóng"` / `Close`, resource-id `com.ss.android.ugc.trill:id/e63`.

## 2. Quy tắc Thao tác Chuẩn (User Rule 2026-08-25)
1. Khi gặp popup này: **Bấm Follow 1 đến 2 nick** trong danh sách gợi ý trước (mỗi lần bấm delay ~0.8s và recapture XML).
2. Sau khi bấm 1–2 nick: **Bấm nút Đóng ✕** (`e63` / `"Đóng"`) để giải phóng toàn bộ popup về màn hình gốc.

## 3. Ràng buộc An toàn 3 Lớp Chống Bấm Nhầm (Spatial & Anchor Guards)
Tránh tuyệt đối việc script quét trúng và bấm nhầm nút Follow ngoài Feed, Live hoặc Profile:
- **Khóa 1 (Title Anchor):** BẮT BUỘC tồn tại node tiêu đề `"Follow bạn bè của bạn"` trên cây XML. Nếu không có $\rightarrow$ Dừng ngay, không tìm nút Follow.
- **Khóa 2 (Spatial Bounding):** Nút Follow bắt buộc phải có tọa độ $y > y_{title}$ (nằm bên dưới tiêu đề popup) và `resource-id` là `:id/thb` (hoặc `class="android.widget.Button"`).
- **Khóa 3 (Limit & Verification):** Bấm tối đa 2 nick $\rightarrow$ đóng X $\rightarrow$ xác minh XML không còn popup.

## 4. Kích Hoạt Tại Mọi Giai Đoạn
Popup này có thể nhảy ra ở:
1. **Preflight / Chuyển nick:** Handled bởi `benign_popup_registry`.
2. **Trong khi lướt Feed (sau mỗi swipe):** Handled bởi `_maybe_dismiss_allowed_popup_after_swipe`.
3. **Đối soát Profile cuối phiên (`_verify_profile_after_session`):**
   - Khi vừa tap vào tab Hồ sơ, nếu gặp popup che khuất header Profile $\rightarrow$ tự động gọi `dismiss_follow_friends_suggestion_popup` trước khi đọc `@username`, ngăn chặn lỗi false-positive `profile account mismatch`.
