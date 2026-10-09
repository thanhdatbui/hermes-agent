# Case UI-63: TikTok 46.9.3 ID/FM9 Drift, Optimistic UI Lừa Đảo & Re-entry Ground Truth

## 1. Hiện Tượng & Root Cause
- **TikTok 46.9.3 Selector Drift**: Trên Samsung Galaxy S7 (máy 38), TikTok thay đổi resource-id nút Follow/Follow lại và nút Nhắn tin trên trang cá nhân sang `id/fm9` (cả 2 nút cùng mang chung id `id/fm9`).
  - Trong `verify_follow.py`, whitelist `_ACTION_BUTTON_SUFFIXES` thiếu `:id/fm9` và `id/fm9`.
  - Node Follow mang id `fm9` bị `_is_profile_action_node` bỏ qua, trong khi nút "Nhắn tin" mang text khớp `message_markers` -> profile chưa follow bị classify nhầm thành `"followed"`.
  - **Hậu quả**:
    - Mode 1: Search nick chưa follow, vào profile thấy id/fm9 classify nhầm thành "followed" -> script tưởng đã follow sẵn nên đưa vào danh sách `skipped` rồi back ra ngoài mà không hề tap nút!
    - Mode 2: Anchor chưa follow, vào profile thấy id/fm9 classify nhầm thành "followed" -> nhảy vào list Following cào tiếp dù anchor chưa follow.
    - Path B: Profile nick con verify bị lọt lưới, báo cáo thành công giả.

- **Optimistic UI / Local Activity Cache Lừa Đảo (False Positive)**:
  - Khi bấm Follow (trên Video Player hoặc Profile), TikTok Android chạy local animation lập tức đổi nút sang "Nhắn tin" trên Profile và "Đã follow" ngoài danh sách.
  - **Thực tế Server**: Server TikTok từ chối (silent rollback / rate-limit), nhưng do local cache trong RAM của Activity stack, script bị đánh lừa là đã follow thành công.
  - **Chứng minh thực nghiệm trên máy 38**: Khi thoát ra mở lại profile mới từ đầu (Fresh Re-entry), nút lập tức văng ngược lại màu đỏ "Follow lại" (`not_followed`).

## 2. Quy Tắc Khóa Cứng (System Invariants)
1. **Selector Engine Fail-Closed**:
   - `UNKNOWN` UI state = LỖI HỆ THỐNG (`MANUAL_REVIEW / SELECTOR_DRIFT`), TUYỆT ĐỐI CẤM tự đoán, CẤM silent-success, CẤM skip.
   - Bổ sung ngay `:id/fm9` và `id/fm9` vào `_ACTION_BUTTON_SUFFIXES`.
2. **Anchor Follow Fail-Closed**:
   - Trong `_ensure_anchor_followed`, CHỈ cho phép tiếp tục khi và chỉ khi trạng thái đạt tuyệt đối `followed`. Mọi trường hợp không nhận follow sau reload đều lập tức gọi `set_follow_failed()` ngắt phiên ngay, cấm nhảy vào cào list Following của Anchor.
3. **Phân Bổ Tự Nhiên Xem Video (Sol Approved)**:
   - Khi vào profile: Chọn ngẫu nhiên 1 video từ các video hiển thị trên lưới (`random.choice(video_covers[:min(len(video_covers), 6)])`), cấm bấm cố định `video_covers[0]`.
   - Phân bổ: 70% xem 1 video (6-12s, like 40%), 25% lướt thêm video thứ 2 (4-8s), 5% lướt thêm video thứ 3.
4. **Đối Soát Server Truth Qua Re-entry & Ground Truth Delta**:
   - Trạng thái trên Profile vừa tap là Optimistic UI giả.
   - Bắt buộc phải có Re-entry kiểm tra server state thật. Nếu nút vẫn đỏ -> kích hoạt `state.set_follow_failed()`, dừng phiên ngay và đưa máy vào Cooldown.
   - Cào Profile acc farm trước và sau ca chạy trên toàn bộ Row để lấy Delta `Đang follow` thực tế đối soát với số lượng script báo.
