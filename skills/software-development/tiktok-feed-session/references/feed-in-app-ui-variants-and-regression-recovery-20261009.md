# TikTok In-App Feed UI Variants & Regression Gate Recovery (09/10/2026)

## 1. Thẻ Đề Xuất Bạn Bè / Follow Lại (`follow_back_suggestion`)
- **Hiện tượng**: Trên tab Bạn bè hoặc For You, TikTok hiển thị thẻ đề xuất tài khoản / bạn bè với nút *"Follow lại"* (`id/ubp`).
- **Biến thể UI mới**:
  - Bản cũ: Nút đóng/bỏ qua là *"Không quan tâm"* (`id/cv6`).
  - Bản mới (v47.x): Nút đóng/bỏ qua đổi thành nhãn **`"Xóa"`** (`resource-id="com.ss.android.ugc.trill:id/udr"`).
- **Quy tắc an toàn Farm (Invariant)**:
  - **TUYỆT ĐỐI CẤM** tap vào nút *"Follow lại"* (`id/ubp`) trên Feed vì sẽ làm tăng đột biến follow ngoài kế hoạch và kích hoạt TikTok Action Block / Silent Drop.
  - Bộ quét bắt buộc tìm cả hai biến thể:
    `//node[@text="Không quan tâm" or @content-desc="Không quan tâm" or @text="Xóa" or @content-desc="Xóa" or @resource-id="com.ss.android.ugc.trill:id/cv6" or @resource-id="com.ss.android.ugc.trill:id/udr"]`
  - Nếu không tìm thấy nút đóng, áp dụng cơ chế swipe fallback để lướt qua thẻ.

---

## 2. Màn Hình Tìm Kiếm Live Suggestions (`tiktok_search_landing_page`)
- **Hiện tượng**: Khi lướt feed, thao tác chạm nhầm hoặc gesture mở màn hình Tìm kiếm với ô nhập `EditText` (`id/hvg`).
- **Lỗ hổng cũ**: `detect_search_landing_page` chỉ nhận diện khi có các cụm từ section tĩnh ("tìm kiếm gần đây", "bạn có thể thích"). Khi người dùng/hệ thống đã gõ ký tự vào ô tìm kiếm (ví dụ `text="6"`), các section tĩnh này biến mất, nhường chỗ cho danh sách gợi ý tự động (`resource-id="com.ss.android.ugc.trill:id/tvl_unified_sug"`). Điều này làm detector trả về `None`, đẩy màn hình thành `unknown` và gây kẹt runner.
- **Biện pháp nhận diện chuẩn xác**:
  - Nhận diện khi có `has_search_input` (`EditText` hoặc `id/tv_search_input`) kết hợp với nút tìm kiếm (`id/tv_search_textview` / `"Tìm kiếm"`) HOẶC có các node gợi ý (`rids` chứa `"sug"` / `tvl_unified_sug`).
  - Handler xử lý: Bấm nút Back (`id/bse` hoặc `input keyevent 4`) để thoát khỏi màn hình tìm kiếm về lại Feed.

---

## 3. Màn Hình Trang Cá Nhân Creator Bị Cuộn (`_is_public_profile_screen`)
- **Hiện tượng**: Chạm nhầm avatar/username của creator trên feed làm mở trang cá nhân của họ.
- **Lỗ hổng cũ**: Khi trang cá nhân bị cuộn xuống qua các lượt swipe recovery, phần header chứa `@username` và stats bị trôi khỏi màn hình. Hàm `_is_public_profile_screen` đòi hỏi bắt buộc phải có `@username` nên phân loại màn hình thành `unknown`. Runner cố vuốt thêm nhưng vuốt trên profile chỉ cuộn tiếp danh sách video.
- **Biện pháp nhận diện scrolled profile**:
  - Nhận diện khi có $\ge 3$ phần tử view count video (`resource-id="com.ss.android.ugc.trill:id/tv_play_count"`), có nút trạng thái follow (`"Follow"`, `"Đang follow"`, `"Đã follow"`), và không có thanh điều hướng đáy (`"Trang chủ"`, `"Home"`).
  - Phân loại chuẩn xác là `profile`. Luồng `feed_swipe_smoke` đã có sẵn cơ chế khi gặp `detected_screen == "profile"` sẽ gửi `input keyevent 4` (Back) để thoát về Feed.

---

## 4. Kỷ Luật Regression Gate & Closeout Gate (Pytest)
- Mọi bản vá lỗi nhận diện màn hình BẮT BUỘC phải đi kèm unit test regression:
  1. `tests/test_feed_swipe_smoke_popups.py`: Test tap đóng nút *"Xóa"* (`id/udr`).
  2. `tests/test_benign_popup.py` / `tests/test_classifier.py`: Test nhận diện search suggestions có `tvl_unified_sug`.
  3. `tests/test_classifier.py`: Test phân loại scrolled profile grid (`tv_play_count` $\ge 3$) thành `profile`.
- **Closeout Gate**: Bắt buộc chạy `closeout_gate.py` để Reviewer Sol Auditor chấm điểm $\ge 85/100$ trước khi push lên remote `origin/master`.
