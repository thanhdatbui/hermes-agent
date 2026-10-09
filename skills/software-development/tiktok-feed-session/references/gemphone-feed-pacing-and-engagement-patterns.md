# TikTok Feed Pacing & Engagement Patterns (GemPhone Benchmark)

Tài liệu tham chiếu chuẩn hóa hành vi lướt nuôi tài khoản từ thực nghiệm 144 máy và workflow GemPhoneFarm gốc (14/09/2026).

---

## 1. Bản chất Thuật toán Anti-Fraud TikTok (Phản biện từ Claude CLI & GPT Sol)
- **Không có chuyện cộng điểm cơ học**: TikTok không chấm trust score theo kiểu xem 1 video = +10 điểm, like = +5 điểm.
- **Phát hiện bất thường (Anomaly Detection)**: Hệ thống AI của TikTok quét sự đồng điệu hành vi (Behavior Fingerprint Similarity) trên toàn bộ dải IP, subnet và cụm thiết bị (Device Cluster).
- **Rủi ro kịch bản rập khuôn**: 100 máy cùng lướt theo một tốc độ, cùng tỷ lệ like cố định, hoặc quỹ đạo quẹt thẳng đứng 100% ($dx = 0$) sẽ bị xếp vào nhóm Bot Farm.

---

## 2. Ngẫu nhiên hóa Tỷ lệ Like đa Tab (Case 166)
- Tab **Following (Đang follow)**: Biến thiên ngẫu nhiên `30% – 60%` mỗi phiên.
- Tab **Friends (Bạn bè)**: Biến thiên ngẫu nhiên `50% – 80%` mỗi phiên.
- Tab **For You (Đề xuất)**: Giữ mức tự nhiên `8%`.

---

## 3. Phân nhánh Thẻ Gợi ý Bạn bè / Follow lại trên Feed (Case 165)
- Khi gặp thẻ `follow_back_suggestion`:
  - Nick đang bị phạt nhả follow (`is_account_in_follow_cooldown == True`): Bắt buộc tap **"Không quan tâm"** để tránh bị tính vi phạm tiếp.
  - Nick sạch (`is_account_in_follow_cooldown == False`): Bấm **"Follow lại"** / **"Theo dõi lại"** để tạo tương tác chéo tự nhiên.

---

## 4. Hành vi Bookmark / Favorite (Bấm Lưu video)
- Hành vi người dùng thật: Video thực sự hay thì mới thả tim, và trong số video đã thả tim thì mới có một tỷ lệ nhỏ (15% - 30%) được bấm **"Lưu"** vào mục Yêu thích.
- Điểm tin cậy của lượt Lưu cao hơn nhiều so với lượt Like đơn thuần.
