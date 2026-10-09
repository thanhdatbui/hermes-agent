# Sol Consultant & TikTok Farm Anomaly Standards

## 1. Cơ chế triệu hồi Sol ("Gọi Sol hỏi")
- **Bản chất**: Sol là persona/chuyên gia vận hành Phone Farm 160 máy, chạy trên model `GPT-5.6 Sol` thông qua OmniRoute proxy tại local:
  - Endpoint: `http://127.0.0.1:20129/v1/chat/completions`
  - Model khả dụng: `chatgpt-web/gpt-5.6-sol-instant` (phản hồi nhanh) hoặc `chatgpt-web/gpt-5.6-sol-high` (suy luận sâu).
- **Kỷ luật điều phối**: CẤM TUYỆT ĐỐI Coordinator nói "không có kênh gọi trực tiếp tên Sol". Khi user bảo "Gọi Sol hỏi" hoặc "hỏi Sol xem", Agent gửi request HTTP POST tới OmniRoute `:20129` lấy phán quyết thực tế của Sol và báo cáo lại sếp Kibe.

## 2. Quy chuẩn chẩn đoán Shadowban & 0-FYP (Khuyến nghị thực chiến từ Sol)
- **Tụt follow nhỏ lẻ (-1, -2)**: Hoàn toàn là jitter tự nhiên (bot dạo bị TikTok quét hoặc unfollow ngẫu nhiên). TUYỆT ĐỐI KHÔNG coi là shadowban.
- **Tín hiệu Shadowban / Flop phân phối thực sự**:
  1. **Tỷ lệ rớt follow (`drop_rate`)**:
     $$\text{Drop Rate} = \frac{-\Delta Follower}{\text{Follower cũ}} \times 100\%$$
     - Với nick $< 1.000$ follow: Tụt $\ge -5$ hoặc $\text{drop\_rate} \ge 1.0\%/24h$ mới vào diện theo dõi bất thường (`is_anomaly_drop`).
     - Tụt $< 0.5\%$: Bỏ qua hoàn toàn, không spam cảnh báo.
  2. **Nghi ngờ 0 FYP (Tê liệt phân phối video)**:
     - Thỏa mãn: Đăng thêm video mới ($\Delta Video > 0$) nhưng lượt tim hoàn toàn đứng hình ($\Delta Heart == 0$) sau chu kỳ quét.
     - Nếu xảy ra liên tiếp trên 2–3 video mới: Dấu hiệu nick bị bóp phân phối / không lọt vào luồng test FYP. Cần kiểm tra lại IP/proxy của máy và ngưng tool follow dạo 48h để dưỡng sinh.
