# Case UI-63: TikTok 46.9.3 Selector Drift (id/fm9), Server Truth via Following List Row, and Natural Adaptive Video Engagement

## 1. Hiện tượng & Vấn đề thực tế (Phát hiện tại Farm ngày 20/09/2026 trên Máy 38)
1. **Selector Drift TikTok 46.9.3**:
   - TikTok đổi id nút quan hệ trên profile thành `id/fm9` (cả nút "Follow"/"Follow lại" và "Nhắn tin" đều dùng resource-id `id/fm9`).
   - Cũ: Whitelist `_ACTION_BUTTON_SUFFIXES` thiếu `":id/fm9"` và `"id/fm9"`.
   - **Hậu quả nghiêm trọng:** Node Follow `id/fm9` bị parser coi là không phải action button, trong khi node "Nhắn tin" lọt qua vì chứa text "Nhắn tin". Runner phân loại nhầm profile chưa follow thành `followed`!
   - **Biểu hiện:**
     - Mode 1: Search nick chưa follow, vào profile thấy id/fm9 -> tưởng đã follow -> ghi `skipped` và back ra ngoài không hề tap nút.
     - Mode 2 Anchor: Anchor chưa follow nhưng parser tưởng `followed` -> nhảy ngay vào tab Following cào nick con dù anchor ngoài đời vẫn hiện Follow đỏ.
     - Mode 2 Path B: Khi mở profile nick con kiểm tra, không bắt được nút nhả follow đỏ mà tưởng nhầm thành công, dẫn đến báo cáo thành công giả (False Positive).

2. **Cơ chế Cache Cục Bộ của TikTok Android (Local Activity Stack Cache)**:
   - Khi bấm Follow trên video player hoặc profile, nếu chỉ back về Profile thì TikTok Android vẫn giữ cache cũ của Fragment/Activity, nút trên Profile có thể vẫn hiện màu đỏ hoặc trạng thái cũ dù server đã nhận, hoặc ngược lại hiện "Nhắn tin" nhưng server đã nhả.
   - **Ground Truth duy nhất:** BẮT BUỘC back hẳn ra ngoài danh sách Following (hoặc Search list). Khi đó RecyclerView mới nạp lại dữ liệu từ server và cập nhật chính xác trên Row của nick đó.

3. **Cơ chế Xem Video Tự Nhiên (Human-like Video Engagement - Sol Approved)**:
   - Cũ: Cố định bấm video đầu tiên `video_covers[0]` và xem sau khi đã bấm follow (ngược đời).
   - Mới: Chọn video ngẫu nhiên từ lưới (`random.choice(video_covers[:6])`), lướt xem video TRƯỚC khi follow.
   - Phân bổ tự nhiên: 70% xem 1 video (6-12s), 25% lướt xem 2 video (4-8s), 5% lướt xem 3 video.

---

## 2. Các nguyên tắc Invariant được chuẩn hóa

### Invariant 1: Unknown UI State = Fail-Closed (MANUAL_REVIEW), CẤM tự đoán
- Trong automation farm: Trạng thái UI chỉ có 3 loại:
  1. `not_followed` (Nút Follow/Follow lại).
  2. `followed` (Nút Nhắn tin/Following).
  3. `unknown` (Layout lạ, selector drift).
- Khi gặp `unknown`: **BẮT BUỘC BÁO LỖI (MANUAL_REVIEW / SELECTOR_DRIFT) VÀ DỪNG SESSION NGAY LẬP TỨC**. Tuyệt đối cấm fallback, cấm assume followed, cấm silent skip.

### Invariant 2: Anchor Gate Fail-Closed
- Trong `_ensure_anchor_followed`: CHỈ cho phép tiếp tục khi và chỉ khi trạng thái đạt `followed`. Nếu không theo dõi được anchor hoặc bị nhả -> set `FOLLOW_FAILED` và dừng session ngay lập tức, cấm tuyệt đối nhảy vào list Following của anchor.

### Invariant 3: Server Truth qua Following List Row
- Sau khi bấm follow nick trong list: BẮT BUỘC back hẳn ra danh sách Following để RecyclerView đồng bộ trạng thái server.
- Nút trên Row là `Đã follow` / `Bạn bè` -> Server đã nhận thật 100%.
- Nút trên Row vẫn là `Follow` / `Follow lại` đỏ -> TikTok đã âm thầm nhả -> phanh dừng session ngay lập tức (`FOLLOW_FAILED`), đưa acc vào cooldown.

### Invariant 4: Đối soát Ground Truth Delta (Audit Layer)
- Cào profile acc farm trước ca: `Following Before`.
- Cào profile acc farm sau ca: `Following After`.
- Đối chiếu: `Actual Delta (After - Before)` phải bằng số lượng Script báo thành công. Nếu script báo 15 mà Delta = 0 -> phát hiện ngay rollback / shadow-block.
