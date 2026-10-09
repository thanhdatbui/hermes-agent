# Kỷ luật Phân bổ Video Nuôi Nick & Quản lý Kho Video Gốc (45 Clip là MIN, không tạo thư mục đệm lắt nhắt)

## 1. Nguyên tắc cốt lõi: 45 clip là MIN, KHÔNG PHẢI MAX
- Quy chuẩn tối thiểu cho 1 kênh nuôi an toàn là **45 clip** (~5 tháng với tần suất 3 ngày/clip).
- Tuyệt đối **không giới hạn cứng ở 45 clip**: Nếu nguồn kênh download về được 60, 70 hay 100 clip chất lượng cao, đẩy **toàn bộ vào thẳng thư mục của kênh đó** (`D:\video goc\<folder_id>`).
- Việc nuôi nick có 60–70 clip thành phẩm giúp tài khoản nuôi liên tục 7–8 tháng mà không bao giờ lo hết đạn hoặc phải can thiệp thủ công nhiều lần.

## 2. Cấm tạo thư mục đệm / gối đầu lắt nhắt (`folder_goi_dau_dot2`)
- **Tập trung hóa dữ liệu**: Mọi video thuộc về 1 kênh / 1 nick phải nằm tập trung duy nhất tại `D:\video goc\<folder_id>` và render thẳng ra `D:\TIKTOK-videonuoinick\<folder_id>`.
- **Tuyệt đối không tạo các folder phụ** như `<folder_id>_goi_dau_dot2`, `<folder_id>_extra`... gây phân mảnh dữ liệu, khó kiểm soát và làm rối logic đồng bộ.
- Phần video dư thừa của kênh (sau khi đã nạp đủ số lượng lớn cho kênh chính, ví dụ >70 clip) sẽ được dồn vào **Bể gộp đa kênh (`D:\video goc\curated_pool`)** để chia sẻ cho các kênh tổng hợp / kênh thiếu hụt khác trong farm.

## 3. Quy trình nạp bù và vá Render bằng cờ `--resume-verify-existing`
Khi một folder được bổ sung thêm video gốc (từ 45 lên 70 clip) hoặc khi gặp lỗi ffmpeg hỏng 1 vài clip giữa chừng:
1. Đảm bảo tên video gốc đánh số chuẩn thứ tự `1.mp4, 2.mp4, ..., N.mp4`.
2. Chạy lệnh render với cờ `--resume-verify-existing`:
   ```bash
   python D:/Taadaa/Tiktok-video/scripts/random_batch_render.py \
     --input-dir "D:/video goc/<id>" \
     --output-dir "D:/TIKTOK-videonuoinick/<id>" \
     --preset "D:/Taadaa/Tiktok-video/presets/preset_owner.json" \
     --randomize \
     --parallel 2 \
     --resume-verify-existing
   ```
3. Script sẽ tự động kiểm tra `ffprobe` các clip thành phẩm đã có từ trước (skip qua không tốn tài nguyên) và chỉ render các clip mới bổ sung hoặc clip bị hỏng.
