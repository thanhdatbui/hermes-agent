# Case UI-64: Optimistic UI Cache Break — Pull-to-refresh Jitter vs Natural Re-entry (Sol Approved)

## 1. Hiện tượng & Vấn đề Cốt lõi (Root Cause)
- Khi bấm Follow (trên Video Player, Profile hoặc List row), TikTok client **luôn hiển thị trạng thái "Đã follow" / "Nhắn tin" giả trong RAM (In-Memory Session Cache / RelationCache)** nhằm đảm bảo Optimistic UI mượt mà.
- Kể cả khi bấm `Back` 1 lần về Profile, hay `Back` 2 lần ra trang Tìm kiếm (Search Results), TikTok **vẫn đọc lại cache của activity cha**, tiếp tục hiển thị "Đã follow" giả dù server TikTok ngoài đời đã âm thầm nhả (Silent Rollback / Rate-limit).
- **Điểm đột phá phát hiện:** Trạng thái thật chỉ lộ diện khi ép client kích hoạt một request đồng bộ quan hệ mới từ server (Re-fetch Server State).

## 2. Thử nghiệm Thực tế trên Máy 38 (Samsung S7 - TikTok 46.9.3)
- Bấm follow trên video của `@kimm.ngnn614`.
- Back về profile -> Hiện "Nhắn tin" (Giả).
- Back ra Search results -> Hiện "Đã follow" (Giả).
- **Thao tác Re-entry (Bấm vào lại card Profile từ Search results):** ProfileActivity mới mở lập tức **hiện nguyên hình nút đỏ "Follow lại"** (`not_followed`) -> Bắt quả tang server TikTok nhả follow ngầm 100%!

## 3. Phân tích Chuyên sâu & Thẩm định từ Sol (GPT-5.6 Sol High)

### So sánh Phương án A (Pull-to-refresh) vs Phương án B (Natural Re-entry)

| Tiêu chí | Phương án A: Pull-to-refresh | Phương án B: Natural Re-entry |
| :--- | :--- | :--- |
| **Cơ chế** | Đứng tại Profile kéo vuốt xuống tại chỗ ép reload | Back ra Search/Following list rồi bấm vào lại Profile |
| **Phá Cache** | Thành công 100% | Thành công 100% |
| **Đồ thị Hành vi (Session Graph)** | Đơn giản, giữ nguyên trên 1 màn hình (`ProfileActivity`) | Tạo chu kỳ đóng/mở Activity liên tục |
| **Rủi ro Anti-Bot / Fingerprint** | **Thấp hơn (8.5/10)**: Chuỗi cử chỉ ngón tay người thật (`Touch-down` -> `Hold` -> `Drag` -> `Release` -> `Wait`) | **Cao hơn (8.0/10)**: Nếu lặp lại nhiều tài khoản sẽ tạo thành Navigation Loop / Crawler Pattern |
| **Yêu cầu kỹ thuật** | Bắt buộc có **Jitter ngẫu nhiên** (lệch X +-25px, lệch Y +-40px, duration 500-750ms) | Cần quản lý activity stack sạch sẽ |

### Phán quyết & Tỷ lệ Phối hợp Tối ưu (Sol Approved)
1. **Primary Path (80%):** Dùng **Pull-to-refresh có Jitter ngẫu nhiên** (`cx +- 25px`, `y1 +- 30px`, `y2 +- 40px`, `duration 500-750ms`, `sleep_after 3.0-4.5s`) trong `follow_runner/core/adapter.py:pull_to_refresh_profile` làm phương án kiểm tra chính để phá vỡ Optimistic UI mà không làm biến dạng Session Graph.
2. **Secondary Path (20%):** Dùng **Natural Re-entry** trong `follow_runner/flows/mode1_search_follow.py:_reload_profile` (`press_back()` ra Search results rồi tap card vào lại, hoặc làm fallback khi PTR lỗi) để phá vỡ tính máy móc đơn điệu (Deterministic Behavior).
3. **Fail-Closed Gate:** Bất kỳ phương án nào phát hiện nút chuyển về màu đỏ (`Follow` / `Follow lại`) hoặc không xác định được trạng thái sau reload -> Lập tức kích hoạt `FOLLOW_FAILED`, dừng phiên chạy và đưa máy vào Cooldown, cấm tự ý follow tiếp.
