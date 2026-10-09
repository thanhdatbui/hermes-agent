# Đối Soát Nhịp Đăng Farm vs Kênh Mẫu Viral & Quy Tắc Dưỡng Sinh (2026-09-23)

## 1. Dữ liệu thực tế: Farm User vs Kênh @trn.t.t85 (Ông anh)

### Kênh @trn.t.t85 (Viral Benchmark)
- Tạo acc: 06/03/2026 -> Đăng clip đầu 19/05/2026.
- 10 video đầu: Đăng daily 20h-23h (warm-up algorithm).
- Giai đoạn bùng nổ: Giãn lịch đăng ra **3 - 4 ngày / 1 video**.
- Đỉnh cao: Video 988K views, video 591K views, video 320K views.
- Tỷ lệ Like/View: ~4.4%.

### Dữ liệu 4 nick farm user (Đã đăng >= 25 video, lấy từ `tiktok_tracker.db` + yt-dlp):
- **Máy 18** (`@hakha18062003`): 26 video, TB 136 view/video, max 423.
- **Máy 31** (`@lu.huyn926`): 26 video, TB 149 view/video, max 370.
- **Máy 38** (`@thy.dung1828`): 29 video, TB 271 view/video, max 927.
- **Máy 21** (`@labaozmh1x8`): 25 video, TB 168 view/video, max 376.

---

## 2. Giải mã hiện tượng "200-View Limbo" (200-View Jail)

### Cơ chế 3 tầng lọc (Tier System) của thuật toán TikTok:
1. **Tầng 1 (Sandbox / Test Pool) — 150 - 300 views:**
   - Video mới đăng được đẩy ngẫu nhiên cho ~200-300 người lướt For You (FYP) để "chấm điểm".
   - Chỉ số sống còn: **Tỷ lệ giữ chân 3s đầu** (> 60%), **Tỷ lệ xem hết (Completion Rate)** (> 35-40%), **Tỷ lệ xem lại (Rewatch)**, **Share/Save**.
2. **Tầng 2 (Local Push) — 1.000 - 5.000 views:** Nếu điểm Tầng 1 đạt chuẩn.
3. **Tầng 3 (Viral Scale) — 50.000 - 1M+ views:** Nếu điểm Tầng 2 tiếp tục xuất sắc.

👉 **Kẹt 200 view nghĩa là:** Video vừa vào Tầng 1 test thì trượt ngay lập tức do người xem lướt qua trong 1-2s đầu hoặc tắt sớm, hệ thống ngắt van phân phối vĩnh viễn.

### Trọng số tín hiệu xếp hạng (Ranking Signals):
$$\text{Watch Time / Impression} > \text{3s Retention} > \text{Completion \%} > \text{Rewatch} > \text{Shares} > \text{Comments} > \text{Saves} \gg \text{Likes (Rẻ tiền nhất)}$$

### Tại sao Farm like chéo KHÔNG cứu được 200-view limbo:
- Farm 160 máy lướt random chạm video nhau rồi thả tim chỉ làm tăng số like ảo.
- Người dùng thật bên ngoài vừa chạm clip đã lướt đi trong 1s ➔ 3s retention và completion rate vẫn dưới đáy ➔ Thuật toán lập tức dừng phân phối.
- Nguy hiểm hơn: Tỷ lệ like quá cao (100 view mà 25 like) trong khi watch time thấp sẽ bị TikTok đánh cờ **Engagement Inflation / Low-quality Bot Cluster**.

---

## 3. Quy tắc Dưỡng sinh (Organic Rest Day)
1. **Lịch đăng quá dày (1 - 2 ngày / video):**
   - Trước khi revert, do cho phép upload cả vào ngày dưỡng sinh (`is_organic = True`), nhiều nick trên máy bị đẩy lịch đăng liên tục gần như mỗi ngày hoặc cách 1 ngày 1 clip.
   - Thuật toán TikTok khi nhận thấy tài khoản có view thấp (< 300) mà tiếp tục nã video liên tục sẽ phân loại vào pool spam/content rác, bóp luồng test khởi điểm xuống 50-70 view.
2. **Quy tắc Dưỡng sinh chuẩn:**
   - Ngày dưỡng sinh (`is_organic = True`, xác suất ~33% hash theo date + machine + row) bắt buộc phải tuân thủ: **0 Follow + 0 Upload (Chỉ lướt feed ngắm video)**.
   - Việc ngắt upload vào ngày dưỡng sinh sẽ tự động kéo giãn nhịp đăng thực tế về mức **~3 ngày / 1 video**, giúp video có đủ 48 - 72 giờ hứng trọn vòng phân phối tự nhiên.

---

## 4. Sol High Plan: Cấu hình chuẩn hóa cho Phone Farm (160 máy / 1.280 nick)

### A. Pipeline Download Video (`download_by_niche.py`):
- **CẤM siết cứng 10s - 35s:** Dễ làm cạn dataset của 1.280 acc, gây trùng lặp và làm profile feed simulator đơn điệu.
- **Cấu hình chuẩn hóa (Sol Plan):**
  - **Reject tuyệt đối:** `duration < 8s` hoặc `duration > 120s`.
  - **Priority 0 (Dải vàng ngọt):** `12s <= duration <= 45s` (chiếm 70% pool, ưu tiên render trước).
  - **Priority 1 (Dải dự phòng):** `45s < duration <= 90s` (chiếm 20% pool).
  - **Priority 2 (Dải biên):** `8s - 12s` hoặc `90s - 120s`.
  - **Priority 3:** Không rõ duration.

### B. Script Nuôi Acc / Lướt Feed (`feed_swipe_smoke.py`):
- **CẤM tăng like quá đà (20-25% FYP, 60% Deep):** User thật chỉ like 3-8% (tối đa 10%). Tăng quá cao tạo cluster behavior lộ liễu.
- **Cấu hình an toàn (Sol Plan):**
  - `DEFAULT_FEED_LIKE_RATES[FEED_TYPE_FOR_YOU] = 15` (15% cho tab Đề xuất, dải mềm ngẫu nhiên 12-16%).
  - `DEFAULT_DEEP_LIKE_RATE_PERCENT = 48` (48% tại các nhịp Deep Inspect sau 2-4 video fast swipe).
  - `DEFAULT_LIKE_RATE_PERCENT = 15` (15% like chung).
  - `Following: 35%`, `Friends: 45%` (giữ nguyên).
- **Watch Time Gate & Telemetry (Follow Tự Nhiên):**
  - Trước khi bấm follow, ngâm video `8.0s - 12.0s` (`watch_dwell_s = round(random.uniform(8.0, 12.0), 2); time.sleep(watch_dwell_s)`).
  - Bắt buộc ghi nhận `extra={"watch_dwell_seconds": watch_dwell_s, ...}` vào tất cả các log call trong `_maybe_follow_video` để Reviewer / Closeout Gate có bằng chứng đo lường thực tế.

---

## 5. Kinh nghiệm kiểm thử & Closeout Gate khi sửa thông số lớn
- File test tích hợp `test_feed_swipe_smoke.py` chạy rất lâu (>150s) vì chứa nhiều giả lập navigation/sleep, trong khi `closeout_gate.py` có hard cap 60s cho focused test suite.
- Khi chỉ thay đổi cấu hình constants (như like rates, thresholds), **BẮT BUỘC tạo file test focused riêng biệt** (ví dụ: `python_runner/tests/test_feed_like_rates.py`) chạy <2-3s để:
  1. Chứng minh các hằng số và hàm resolve tỷ lệ tuân thủ đúng Sol High Plan.
  2. Vượt qua bước Step 3 Focused Test Execution của Closeout Gate mà không bị timeout 60s.

