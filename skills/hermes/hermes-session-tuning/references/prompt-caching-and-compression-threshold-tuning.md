# Tinh chỉnh Ngưỡng Nén Context Hermes (Prompt Caching & Chống Mất Trí Nhớ)

## 1. Vấn đề khi nén ngữ cảnh quá gắt (`threshold: 0.3`, `protect_last_n: 20`)
- **Tác hại đối với Google Gemini:**
  - Google Gemini có tính năng **Prompt Caching** rất mạnh, giúp giảm 75-80% chi phí đọc token và tăng tốc độ phản hồi.
  - Khi nén sớm ở ngưỡng 30% (~300k tokens), Hermes liên tục cắt vụn lịch sử, phá vỡ cấu trúc prefix cache, làm mất hoàn toàn lợi ích của Prompt Cache.
  - `protect_last_n: 20` khiến đuôi hội thoại quá ngắn, AI mất hết chi tiết kỹ thuật của các bước trước đó, dễ dẫn đến ảo giác và phát ngôn bịa đặt.

## 2. Cấu hình tối ưu chuẩn xác (`config.yaml`)
Để tận dụng tối đa Prompt Cache và giữ mạch suy nghĩ ổn định:
```yaml
compression:
  enabled: true
  threshold: 0.6          # Kích hoạt nén khi context chạm ~600.000 tokens
  target_ratio: 0.2
  protect_last_n: 50      # Giữ nguyên vẹn 50 tin nhắn gần nhất
  protect_first_n: 3      # Giữ nguyên 3 tin nhắn kickoff ban đầu
```

## 3. Quy trình áp dụng & Khởi động lại Gateway
- Khi sửa `config.yaml`, tiến trình Gateway đang chạy trong RAM vẫn giữ cấu hình cũ.
- Bắt buộc phải restart Gateway (qua `Hermes_Gateway.vbs` hoặc `hermes gateway restart`) để nạp giá trị mới vào RAM.
- Luôn chạy script Startup Hook `auto_resume_startup_hook.py` để bảo toàn trạng thái các session đang chạy dở trước khi kill Gateway.
