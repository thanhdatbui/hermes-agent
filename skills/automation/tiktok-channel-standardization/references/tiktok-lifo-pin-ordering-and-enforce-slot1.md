# TikTok LIFO Pin Ordering & Viewport Candidate Sorting Rules (2026-10-30)

## 1. Cơ Chế LIFO Pin Trên TikTok
- **Hành vi thực tế:** Khi ghim bài trên app TikTok, bài bấm ghim sau cùng luôn được đẩy vào **Ô 1** (ngoài cùng bên trái hàng đầu tiên).
- **Thứ tự ghim chuẩn:** Muốn sắp xếp Top 1 (Ô 1), Top 2 (Ô 2), Top 3 (Ô 3):
  * Bắt buộc bấm ghim theo thứ tự tăng dần về view: **Top 3 -> Top 2 -> Top 1**.
  * Bài Top 1 ghim sau cùng sẽ chiếm trọn Ô 1.

## 2. Hàm Tự Động Enforce Slot 1 (`_enforce_top_pin_at_slot1`)
- Luôn bọc gọi hàm `_enforce_top_pin_at_slot1(serial, metrics)` ở cuối luồng `pin_video_on_device`.
- Nếu phát hiện bài nhiều view nhất đang bị dạt sang Ô 2 hoặc Ô 3 (do ghim bài khác sau đó):
  1. Unpin bài top 1 view đó.
  2. Dump UI và parse lại tiles.
  3. Bấm PIN lại đúng bài đó để TikTok đẩy nó trở lại Ô 1.

## 3. Lọc Ứng Viên Candidate Tránh Bẫy View Thấp
- **Sai lầm:** `cands = [t for t in tiles if not t['is_pinned'] and t['views'] >= min_views]` bốc phần tử đầu tiên gặp trong DOM mà không sort, dẫn đến việc chọn nhầm bài rác 3.490 view thay vì bài 21,6K view.
- **Chuẩn hóa:** Bắt buộc sắp xếp giảm dần theo view:
  ```python
  cands = sorted([t for t in tiles if not t["is_pinned"] and t["views"] >= min_views], key=lambda t: t["views"], reverse=True)
  ```
