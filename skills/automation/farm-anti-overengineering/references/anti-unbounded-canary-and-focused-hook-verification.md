# Anti-Unbounded Canary & Focused Hook Verification Rules

## Sự cố: Canary chạy full session làm timeout và chụp ảnh non
- **Nguyên nhân gốc rễ**: Khi kiểm chứng một bản vá nhỏ (ví dụ sửa regex selector, sửa hàm `_open_following_tab`, popup handler), agent chạy cả session/batch pipeline đầy đủ (`run_session` với budget 15-18 follows, chu kỳ video delay 10-15 phút).
- **Hậu quả**:
  1. Hết budget thời gian hoặc lượt gọi tool (timeout 300-360s).
  2. Bị đứt gánh giữa chừng nhưng worker vẫn vội vàng báo cáo hoàn thành.
  3. Bằng chứng nghiệm thu `MEDIA:` bị chụp non (mới mở tới màn hình tìm kiếm `Search landing` chứ chưa tới được màn hình đích mà hàm tác động).

## Kỷ luật thực thi bắt buộc:
1. **Targeted Canary Bounded (<60s)**:
   - Canary BẮT BUỘC chỉ gọi đúng hàm/hook vừa sửa trên 1 target duy nhất.
   - CẤM TUYỆT ĐỐI gọi full session / full budget cho mục đích canary kiểm chứng bug.
2. **Nghiệm thu ảnh tại đúng đích**:
   - Ảnh chụp nghiệm thu `MEDIA:` phải chụp tại thời điểm hàm thực thi xong (màn hình kết quả đích, không chụp màn hình trung gian hoặc landing).
