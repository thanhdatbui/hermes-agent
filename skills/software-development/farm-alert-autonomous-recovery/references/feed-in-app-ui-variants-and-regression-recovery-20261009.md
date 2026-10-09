# Feed In-App UI Variants & Automated Regression Gate (09/10/2026)

## 1. Phân Loại Hiện Trường Thẻ Gợi Ý & Search Suggestions Trên Feed
- **Thẻ đề xuất Bạn bè / Follow lại (`follow_back_suggestion`)**:
  - Giao diện TikTok cập nhật nút loại bỏ thành **`"Xóa"`** (`id/udr`) bên cạnh nút *"Follow lại"* (`id/ubp`).
  - **Quy tắc an toàn Farm**: Tuyệt đối cấm tap *"Follow lại"* (`id/ubp`) vì sẽ phá vỡ hạn ngạch follow và gây nhả follow. Phải tìm và tap nút *"Xóa"* hoặc *"Không quan tâm"*.
- **Màn hình Search Live Auto-complete (`tiktok_search_landing_page`)**:
  - Khi có ký tự trong ô nhập tìm kiếm (`EditText id/hvg`), các section tĩnh biến mất, thay bằng danh sách gợi ý tự động `tvl_unified_sug`.
  - Nhận diện có `has_search_input` và (`has_search_button` hoặc `tvl_unified_sug`) để kích hoạt Keyevent 4 (Back) thoát về Feed.
- **Màn hình Creator Profile bị cuộn (`_is_public_profile_screen`)**:
  - Khi vô tình mở trang cá nhân và cuộn xuống, header chứa `@username` bị khuất, màn hình chỉ còn lưới video `tv_play_count` $\ge 3$ và nút "Follow".
  - Nhận diện đúng `profile` để gửi Keyevent 4 (Back) thoát về Feed thay vì bị dừng `unknown`.

## 2. Quy Chuẩn Regression Gate Tự Động
- Không cập nhật tài liệu ca thủ công (`docs/farm-automation-cases.md`).
- Bắt buộc bổ sung test case trong test suite (`test_classifier.py`, `test_feed_swipe_smoke_popups.py`).
- Cổng thẩm định `closeout_gate.py` phải chạy focused test mapping (< 5s) và đạt điểm Sol Auditor $\ge 85/100$ trước khi push lên `origin/master`.
