# Feed Dismiss, Search Landing, and Scrolled Profile Detection

### 1. Feed Follow Suggestion Dismiss (M19, M68)
- Trên thẻ gợi ý kết bạn / follow lại ("Người bạn có thể biết", "Follow lại"):
  - Nút dismiss có thể hiển thị dưới dạng:
    - `"Không quan tâm"` (resource id `cv6`)
    - `"Xóa"` (resource id `udr`)
  - Rule `follow_back_suggestion` trong `flows/feed_swipe_smoke.py` cần chấp nhận cả hai nhãn và resource id này để dismiss an toàn, tuyệt đối không tap "Follow lại".

### 2. Search Landing with Suggestions (M50)
- Trong `core/benign_popup.py`:
  - Khi user rơi vào màn hình search landing page nhưng có sẵn các suggestion tags/chips (`tvl_unified_sug`), điều kiện nhận diện:
    `(has_search_input and any("sug" in (r or "").lower() for r in rids))`
  - Cần phân loại đúng là `tiktok_search_landing_page` để trigger nút back / dismiss popups.

### 3. Scrolled Public Profile Grid (M26, M49)
- Trong `core/classifier.py`:
  - Khi cuộn sâu vào profile công khai, phần bio header có thể bị ẩn khỏi view XML.
  - Nhận diện màn hình profile dựa trên lưới video play counts (`tv_play_count` >= 3) đi kèm nút trạng thái follow (`follow`, `đang follow`, `đã follow`).
