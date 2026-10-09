# Quy tắc Tối ưu Kho Video: Hạn Mức 45 Clip, Chống Thư Mục Phụ & Kích Hoạt Render Admin Từ Xa

## 1. Tín hiệu & Bài học từ User (Feedback Cốt lõi)
- **Tín hiệu phản hồi của User**: *"Tự nhiên tạo thêm folder chi mệt v đẩy mẹ vào luôn folder kênh đó đi 45 là min chứ đâu phải max"*.
- **Bài học vận hành**:
  1. **45 clip là HẠN MỨC TỐI THIỂU (MINIMUM THRESHOLD), KHÔNG PHẢI TRẦN CỐ ĐỊNH (MAX CAP)**:
     - Kênh nuôi có thể nhận 60–70 clip (nuôi liên tục 7–8 tháng). Càng nhiều clip cùng kênh/niche càng tốt, chống việc phải nạp gối đầu nhiều đợt.
  2. **CẤM TỰ TẠO FOLDER PHỤ LẮT NHẮT (`xxx_goi_dau_dot2`, `xxx_part2`...)**:
     - Mọi video dư cùng nguồn/cùng kênh BẮT BUỘC đẩy thẳng vào thư mục đích (`D:\video goc\<folder_id>`).
     - Đánh số tịnh tiến tiếp tục (`46.mp4`, `47.mp4`, ...), sau đó chạy render nối tiếp với cờ `--resume-verify-existing`.
     - Chỉ video dư khác kênh hoặc cần gom chung cho toàn farm mới đưa vào bể gộp (`D:\video goc\curated_pool`).

---

## 2. Quy trình Bơm Video từ Bể Gộp (`curated_pool`) vào Kênh
Khi cần phân bổ video từ `curated_pool` cho các kênh thiếu clip hoặc chuyển đổi sang 12 niche hot:
1. **Kiểm tra số lượng hiện có**:
   - Nếu thư mục gốc có `< 45` clip $\rightarrow$ Bốc số lượng clip tương ứng từ `curated_pool` bổ sung cho đủ (hoặc vượt) 45 clip.
   - Luôn đánh số nối tiếp chuẩn format số nguyên: `1.mp4, 2.mp4, ...`
2. **Kích hoạt Render Nối tiếp (Resume)**:
   - Dùng lệnh:
     ```bash
     python D:/Taadaa/Tiktok-video/scripts/random_batch_render.py \
       --input-dir "D:/video goc/<id>" \
       --output-dir "D:/TIKTOK-videonuoinick/<id>" \
       --preset "D:/Taadaa/Tiktok-video/presets/preset_owner.json" \
       --randomize --parallel 2 --resume-verify-existing
     ```
   - Nếu gặp lỗi ffmpeg stream/decode hỏng file đơn lẻ (rc=4294967274): Xóa file render lỗi, bốc 1 file mới từ `curated_pool` đè vào file gốc tương ứng và rerun với `--resume-verify-existing`.

---

## 3. Quy trình Khởi động & Giám sát Render trên Máy Admin qua SSH
Khi máy Admin (`192.168.110.119`) có sẵn video gốc trong `D:\video goc may 2` nhưng thư mục render `D:\TIKTOK-videonuoinick-admin` đang trống:
1. **Cơ chế gọi Python từ xa qua SSH (Tránh bẫy Encoding Windows CP1252)**:
   - File script điều phối khi in tiếng Việt ra stdout BẮT BUỘC thêm cấu hình UTF-8 ở đầu file:
     ```python
     import sys
     sys.stdout.reconfigure(encoding='utf-8')
     sys.stderr.reconfigure(encoding='utf-8')
     ```
   - Chạy nền qua `ssh admin-farm` kèm chuyển hướng log:
     ```bash
     ssh -o ConnectTimeout=5 admin-farm "\"D:\Taadaa\python-envs\automation\Scripts\python.exe\" C:\Users\Admin\run_admin_render_worker.py > C:\Users\Admin\render_worker.log 2>&1"
     ```
2. **Kiểm chứng thực tế (Hardware & Process Check)**:
   - Kiểm tra `ffmpeg.exe` xuất hiện trên máy Admin:
     ```bash
     ssh -o ConnectTimeout=5 admin-farm "powershell.exe -Command \"Get-Process -Name ffmpeg | Select-Object Id, CPU, WorkingSet\""
     ```
   - Xem log tiến độ:
     ```bash
     ssh -o ConnectTimeout=5 admin-farm "powershell.exe -Command \"Get-Content C:\Users\Admin\render_worker.log -Tail 30\""
     ```
