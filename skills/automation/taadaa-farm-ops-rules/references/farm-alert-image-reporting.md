# Farm Alert & Incident Image Reporting Pattern

## Context & User Preference
Khi có cảnh báo dừng phiên, lỗi máy farm (như `multi-machine-feed-session`, reg, login, follow, upload), hoặc khi user hỏi về lỗi một máy ("Lỗi l gì v", "sao máy XX dừng"):

1. **BẮT BUỘC gửi ẢNH HIỆN TRƯỜNG THẬT ngay lập tức**:
   - Xác định artifact screenshot của máy tại bước gây dừng (ví dụ: `runtime/kibe/live/.../machines/machine_XX/.../screen.png` hoặc `.ai-runs/...`).
   - Gửi ảnh qua `MEDIA:<absolute_path>` đặt trên một dòng riêng biệt, không bọc markdown, không đưa link text.
   - Luôn gửi kèm ảnh ngay trong câu trả lời giải thích đầu tiên, KHÔNG giải thích suông bằng chữ để user phải gặng hỏi xin ảnh.

2. **Chẩn đoán False Positive với Sponsored / Ad CTA Buttons**:
   - Trong TikTok feed, các video quảng cáo (`Được tài trợ`) của brand (Techcombank, Shopee, v.v.) thường chứa nút CTA màu đỏ/nổi bật có nhãn **"Đăng ký"**, **"Tìm hiểu thêm"**, **"Tải ngay"**.
   - Classifier quét text XML chứa `Đăng ký` có thể gán nhãn nhầm thành `manual-needed:login-overlay` hoặc `manual-needed:login`.
   - Cần đối chiếu giữa UI XML và Screenshot: nếu `Được tài trợ` xuất hiện kèm CTA "Đăng ký" trong feed For You thì đây là sponsored ad feed item, không phải overlay đăng ký tài khoản thật bị out acc.
