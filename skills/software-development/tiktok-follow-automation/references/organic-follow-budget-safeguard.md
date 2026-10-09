# Farm Follow Action Budget & Feed Organic Ratio Safeguard

## 1. Bản chất sự cố Tỷ lệ Follow Tự nhiên quá cao (Feed Organic Cannibalization)
- **Hiện tượng:**
  + Trong các ca nuôi acc (feed session), bot bấm follow dạo ngẫu nhiên trên tab Đề xuất (For You).
  + Khi cấu hình tỷ lệ follow ở mức cũ (5% - 20%), mỗi máy lướt 20-30 video sẽ bấm 1-2 follow ngẫu nhiên.
  + **Hệ lụy trực tiếp:**
    * **Đốt Daily Action Budget:** Trong bối cảnh số máy đủ điều kiện follow chéo trong ngày rất ít (nhiều máy nghỉ dưỡng sinh 1/3 hoặc đang cooldown), mỗi lượt follow dạo ngoài feed nuốt mất 20-30% hạn ngạch hành động an toàn/ngày của nick.
    * **Tỷ lệ Drop/Nhả cực cao:** Do follow tài khoản ngẫu nhiên trên For You mà không xem sâu toàn diện, TikTok spam filter kích hoạt khiến tỷ lệ nhả lên tới **>60%** (ví dụ: bấm 17 lượt bị nhả 11 lượt, chỉ giữ 6).
    * **Lệch Dashboard & Rác Trust:** Ăn mòn trust của nick khi thực hiện follow chéo nội bộ (Mode 1 / Mode 2), gây sai lệch đối soát giữa Bot vs Web.

## 2. Quy chuẩn cấu hình tỷ lệ Siêu thấp (1% Bounded Rate)
- **Quy tắc vàng:** Giữ tỷ lệ follow tự nhiên khi lướt feed ở mức **siêu thấp (1%)**, tuyệt đối không để >= 5%.
- **Vị trí cấu hình chuẩn hóa:**
  1. `python_runner/flows/feed_swipe_smoke.py`:
     - `DEFAULT_DEEP_FOLLOW_RATE_PERCENT = 1`
     - `DEFAULT_FEED_FOLLOW_RATES[FEED_TYPE_FOR_YOU] = 1`
  2. `python_runner/config.example.yaml`:
     - `deep_follow_rate_percent: 1`
  3. `python_runner/tests/test_feed_swipe_smoke.py`:
     - Đồng bộ unit test và phân phối Monte Carlo: Tại 1%, 1.000 lần lướt kỳ vọng ~10 hits (giảm >80% so với mức cũ).

## 3. Bài học điều phối & Kỷ luật tránh over-engineering
- **Tránh giải pháp rườm rà:** Khi xử lý vấn đề action budget, ưu tiên hạ tham số rate về mốc siêu thấp (1%) thay vì viết thêm state machine / bộ đếm theo tuần (weekly rate limit) gây phình to codebase và khó bảo trì.
- **Bảo toàn 98-99% Daily Action Budget:** Toàn bộ hạn ngạch follow hàng ngày phải được ưu tiên tập trung 100% cho chuỗi Follow chéo (Anchor Module 2 & Bù Module 1) để kéo kênh chính đạt KPI.
