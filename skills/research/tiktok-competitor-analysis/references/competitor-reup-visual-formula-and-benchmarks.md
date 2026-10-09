# Công thức Reup Visual / Gái Xinh từ Kênh Mẫu Đối Thủ & Benchmark

## 1. Dữ liệu Case Study thực tế (Đã verify 2026-09-22)

Hai kênh đối thủ được phân tích:
- **Kênh 1:** `@trn.t.t85` (TRần Tý Tý) — 36 video, 2.1M views, 7.6K followers, 88.3K likes.
- **Kênh 2:** `@hong.thy.qunhhh` (Hoàng Thúy Quỳnhhh) — 41 video, 1.7M views, 8.8K followers, 89.6K likes.

Cả 2 kênh do 1 người/1 hệ thống build, cùng chạy chung 1 scheduler/cohort batch (thời điểm đăng cách nhau 6–30 phút, cùng kỳ nghỉ 19 ngày vào tháng 7/2026).

---

## 2. Bốn trụ cột công thức build kênh

### A. Ngâm tài khoản (Aging)
- Tối thiểu **7 ngày** (kênh 2 ngâm tròn 168 giờ; kênh 1 ngâm tới 74 ngày).
- Tránh tuyệt đối việc vừa reg xong nạp video ngay (dễ ăn shadowban hoặc kẹt 0 view).

### B. Mồi thuật toán bằng tệp Following (Seeding Audience)
- Số lượng tích lũy: **650 – 700 nick**.
- **Quy tắc nuôi (User Correction):** KHÔNG follow dồn dập ngay khi tạo nick. Tool nhả tương tác rải rác mỗi ngày hoặc vài ngày một ít theo từng session lướt feed để tích lũy dần trong 2–3 tháng.
- **Phân loại tệp:** Qua phân tích 507 nick đang follow thực tế bằng Chrome CDP, **88.1% là tài khoản gái cá nhân thật**.
- **Tác dụng:** Ép thuật toán TikTok nhận diện gu chủ tài khoản là visual/gái xinh ➔ phân phối video đến đúng tệp người xem tương tự trên FYP.

### C. Chiến thuật nhịp đăng 3 giai đoạn
1. **Giai đoạn Mồi (10–15 ngày đầu):**
   - Đăng **đều đặn mỗi ngày 1 video** (daily).
   - Cố định khung giờ vàng: **21:00 – 22:00 tối** (giờ giải trí cao điểm).
   - View leo tịnh tiến: 900 ➔ 1.500 ➔ 3.000 ➔ 6.000 (không kẹt 200 view).
2. **Giai đoạn Đẩy Viral (Tuần thứ 3–4):**
   - Khi có dấu hiệu cắn đề xuất (>10K view), chuyển khung giờ sang trưa (**11:00 – 13:30**) để đón chu kỳ đẩy FYP buổi chiều.
   - Xuất hiện các clip đột phá: 296K, 591K, 898K, 988K views.
   - Kéo follower từ vài trăm lên thẳng 7K–8K.
3. **Giai đoạn Dưỡng sinh (Sau khi đạt mục tiêu):**
   - Giãn cách **3 – 6 ngày mới đăng 1 video**.
   - Chuyển sang khung sáng (09:00 – 10:30) hoặc chiều muộn (16:00 – 17:30).
   - Duy trì tương tác cơ bản, giữ kênh an toàn chờ chuyển đổi/bán hoặc gắn affiliate.

### D. Tiêu chuẩn kỹ thuật Video
- **Thời lượng:** Giữ chặt trong **13s – 26s** (tối ưu retention / tỷ lệ xem lại).
- **Âm thanh:** Dùng **Original Sound** (âm thanh gốc theo tên kênh) nướng vào video hoặc dùng pipeline FFmpeg 11 tầng (warp speed/pitch, noise floor phá băm, EQ, reverb, chorus, stereo invert, loudnorm -16 LUFS) để tránh bị tắt tiếng bản quyền sau 1–2 tháng.
- **Hashtag:** Dùng 1 bộ cố định ngắn gọn: `#foryou #viral #videoviral #viraltiktok #xuhuong #tiktokvietnam #fyp #trending`.
