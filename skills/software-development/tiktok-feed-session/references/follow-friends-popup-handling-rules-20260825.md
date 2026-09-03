# Quy Tắc Xử Lý Popup "Follow bạn bè của bạn" Trên TikTok Farm (2026-08-25)

## 1. Bản Chất & Phân Biệt Nút Bấm
- **Tiêu đề popup (Anchor):** `Follow bạn bè của bạn` / `Follow your friends`.
- **Nút bấm trên popup:** Nút màu đỏ chữ trắng **`Follow`** (resource-id `com.ss.android.ugc.trill:id/thb`).
  - ⚠️ **Phân biệt:** Nút **`Follow lại`** là của thẻ gợi ý Follow back riêng biệt. Popup "Follow bạn bè của bạn" mục tiêu là nút **`Follow`**.
- **Nút đóng ✕:** Resource-id `com.ss.android.ugc.trill:id/e63` (content-desc `Đóng` / `Close`).

## 2. Quy Trình Xử Lý Chuẩn (Follow 1–2 Nick → Đóng ✕)
1. Phát hiện popup qua tiêu đề `Follow bạn bè của bạn`.
2. Bấm nút **`Follow`** của 1 đến 2 tài khoản gợi ý (delay ~0.8s giữa các lần bấm để xác minh nút đổi trạng thái).
3. Bấm nút **`✕`** (`e63` / `Đóng`) để giải phóng hoàn toàn popup về màn hình trước đó.

## 3. Khóa An Toàn 3 Lớp (Chống Bấm Nhầm Follow Ngoài Màn Hình)
1. **Khóa 1 — Anchor Guard:** BẮT BUỘC tồn tại node tiêu đề `"Follow bạn bè của bạn"` trên cùng cây XML. Nếu không có tiêu đề này $\rightarrow$ TUYỆT ĐỐI không tìm hay tap bất kỳ nút `Follow` nào trên màn hình (tránh tap nhầm tác giả video ở Feed, LIVE, hoặc Profile).
2. **Khóa 2 — Spatial & Resource-ID Guard:**
   - Nút bấm phải có `resource-id` là `:id/thb` (hoặc `class="android.widget.Button"`).
   - Tọa độ $y$ của nút phải nằm dưới tiêu đề popup ($y_{btn} > y_{title}$).
3. **Khóa 3 — Verification & Bounded Loop:**
   - Tối đa 2 lần tap follow.
   - Recapture XML tươi sau mỗi lần tap trước khi tap tiếp hoặc tap nút ✕.

## 4. Phạm Vi Áp Dụng Toàn Diện Ở MỌI Giai Đoạn
- **Giai đoạn 1 (Preflight):** Trước khi lướt feed hoặc switch account.
- **Giai đoạn 2 (In-Feed Swipes):** Sau mỗi lượt swipe lướt video.
- **Giai đoạn 3 (Verify Profile Cuối Phiên):** Đầu hàm `_verify_profile_after_session` trước khi đọc `@username` (ngăn ngừa chặn Profile dẫn đến false mismatch).
