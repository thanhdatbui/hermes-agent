# Case UI-91: Nguy Cơ Ăn Mòn Budget Follow Chéo Từ Follow Tự Nhiên & Kỷ Luật Baseline Lịch Sử (04/10/2026)

## 1. Bối cảnh & Sai Lầm Phổ Biến Của Agent Khi Báo Cáo
- **Sai lầm 1 (Thu hẹp phạm vi thời gian):** Khi người vận hành hỏi tình hình follow "gần đây", agent chỉ nhìn vào 1 ngày gần nhất (24h) thay vì khảo sát dải thời gian đa ngày (7–14 ngày) để thấy được xu hướng tăng/giảm và các đợt siết quét của TikTok.
- **Sai lầm 2 (Nhầm lẫn số lũy kế với sản lượng tháng):** Agent nhìn thấy following của dàn nick già đạt 250–380 và kết luận "tháng này ăn được ngần đó". Thực tế đó là con số lũy kế từ khi tạo nick (tháng 2–7/2026). Khi thiếu snapshot baseline cào Web đầu tháng, tuyệt đối cấm đoán mò sản lượng tăng trưởng của tháng.
- **Sai lầm 3 (Dữ liệu script trước ngày 02/10 không đáng tin cậy):** Trước ngày 02/10/2026 (trước commit `c12242d` vá lỗi nhãn thống kê Profile `id/t_q` Case UI-82 và T0 Scrape), log script bị Optimistic UI của TikTok và regex bắt nhầm nhãn "Đã follow" trên profile thổi phồng rất nặng (script báo 220 lượt nhưng Web chỉ tăng +9). Mọi đo lường tỷ lệ chuyển đổi thật bắt buộc phải lấy từ ngày 02/10 trở đi.

## 2. Tương Tác Giữa Follow Tự Nhiên & Follow Chéo
1. **Thứ tự thực thi trong phiên:**
   - Trong mỗi phiên chạy, máy chạy lướt feed nuôi tương tác (For You / Following / Friends) **TRƯỚC**, sau đó mới kích hoạt module Follow chéo (Mode 1 tìm kiếm hoặc Mode 2 anchor).
2. **Nguy cơ cắn mất Daily Follow Limit:**
   - TikTok áp đặt trust limit và quota follow hàng ngày trên mỗi tài khoản.
   - Do bug `DEFAULT_DEEP_FOLLOW_RATE_PERCENT = 20%` ở nhịp Deep Inspect của fast swipe, mỗi máy cày roll trúng 1–2 follow tự nhiên ngay trong khâu lướt feed.
   - Khi bước sang khâu follow chéo, tài khoản đã bị bào mòn quota an toàn trong ngày, rất dễ kích hoạt cơ chế Anti-Spam của TikTok khiến lượt follow chéo bị nhả nút (Silent Drop / `follow_failed = True`).
3. **Hiện tượng Tỷ lệ % Follow tự nhiên bị phóng đại:**
   - Khi nhiều máy bị nhả follow chéo và ngắt phiên bảo vệ, tổng lượt follow chéo của cả ca bị sụt giảm mạnh (ví dụ từ 500 lượt xuống còn 76 lượt).
   - Trong khi đó, follow tự nhiên của 35 máy cày vẫn gom được 27 lượt.
   - Tỷ lệ $\frac{27}{76} \approx 35.5\%$ tạo cảm giác follow tự nhiên chiếm quá nhiều, nhưng thực chất là do mẫu số follow chéo bị teo tóp.

## 3. Các Invariant Bắt Buộc Ghi Nhớ
- **Organic Rest Day Invariant:** Ngày dưỡng sinh (`is_organic == True`) khóa cứng `_follow_rate = {"for_you": 0, "following": 0, "friends": 0}` (100% không phát sinh follow tự nhiên).
- **Khấu trừ nhả (Released Deduction):** Nếu follow chéo bị nhả ngay lượt đầu (`cnt == 0`), toàn bộ follow tự nhiên của nick đó trong ca bị khấu trừ về 0 trên báo cáo và DB.
- **Reconcile bao phủ cả hai:** Post-session tracker cào Web TikTok tự động đối soát cả danh sách follow chéo thành công (`fl_success`) lẫn nick có follow tự nhiên (`natural_targets`).
- **Khuyến nghị điều chỉnh:** Giảm `DEFAULT_DEEP_FOLLOW_RATE_PERCENT` từ 20% xuống 5% để đồng bộ với rate For You mặc định, hạn chế tối đa việc ăn mòn quota follow chéo.
