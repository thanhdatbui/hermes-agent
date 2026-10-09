# TikTok 46.9.3 Selector Drift, Adaptive Video Watch & Cache-Proof Server Truth

## 1. TikTok 46.9.3 Action Button Drift (`id/fm9`)
- **Triệu chứng:**
  - Trên Samsung Galaxy S7 (Android 8.0, TikTok 46.9.3), TikTok đổi resource-id nút "Follow" / "Follow lại" và "Nhắn tin" thành cùng một id `id/fm9`.
  - Whitelist cũ (`_ACTION_BUTTON_SUFFIXES`) thiếu `id/fm9`.
  - Hậu quả: Node "Follow" bị bỏ qua, trong khi node "Nhắn tin" lọt qua marker `message_markers`, khiến profile chưa follow bị classify nhầm 100% thành `followed`!
  - Ở Mode 1 (search): Runner tưởng nick đã follow sẵn nên đưa vào `skipped` rồi back ra ngoài mà không hề tap nút.
  - Ở Mode 2 (Anchor & Path B): Nhận diện sai trạng thái Anchor và không phát hiện được tình trạng bị nhả follow (tạo false positive / báo cáo thành công giả).
- **Cách khắc phục:**
  - Bổ sung `":id/fm9"` và `"id/fm9"` vào `_ACTION_BUTTON_SUFFIXES` trong `follow_runner/flows/verify_follow.py`.
  - **Invariant Fail-Closed:** Khi profile trả về `unknown` (không nhận diện được layout nút), BẮT BUỘC coi là lỗi hệ thống (`MANUAL_REVIEW / SELECTOR_DRIFT`), dừng session ngay để kiểm tra, CẤM đoán mò hoặc silent-skip.

## 2. Adaptive Video Watch Policy (Sol Approved)
- **Cấm cố định cứng:** Cấm luôn luôn bấm `video_covers[0]` và cấm cố định luôn luôn xem đúng 1 video.
- **Chọn ngẫu nhiên video:** Lấy ngẫu nhiên từ lưới video hiển thị trên profile:
  `random.choice(video_covers[:min(len(video_covers), 6)])`
- **Phân bổ hành vi tự nhiên (Natural Behavior Distribution):**
  - Tỷ lệ chung: ~30% nick ghé thăm được xem video (đảm bảo deadline ca chạy và an toàn RAM cho S7).
  - Trong số các nick được xem video:
    - **70%:** Xem video đầu từ 6–12s, ngẫu nhiên thả tim 40%, back về profile.
    - **25%:** Vuốt xem tiếp video thứ 2 từ 4–8s, ngẫu nhiên thả tim, back về profile.
    - **5%:** Vuốt xem tiếp video thứ 3 lướt nhanh rồi back về profile.

## 3. Cache-Proof Server Truth (Ground Truth trên RecyclerView)
- **Cơ chế cache của TikTok Android:**
  - Bấm Follow trên Video Player, khi back lần 1 về Profile, TikTok vẫn giữ Fragment/Activity trong cache cục bộ, nút trên Profile có thể vẫn hiện màu đỏ hoặc chưa cập nhật.
  - **Ground Truth duy nhất là danh sách Following (RecyclerView):** Bắt buộc back hẳn ra danh sách Following của Anchor (`adapter.back()` và xác nhận `_on_follower_list`).
  - Đọc lại trạng thái nút trên chính dòng (Row) của nick đó:
    - Nếu nút trên Row đổi sang `Đã follow` / `Bạn bè` -> Server đã nhận thật 100%.
    - Nếu nút trên Row vẫn là `Follow` / `Follow lại` đỏ -> TikTok âm thầm nhả follow -> kích hoạt `FOLLOW_FAILED`, dừng phiên ngay lập tức, không bấm tiếp nick sau.
