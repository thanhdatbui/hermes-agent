# Chẩn đoán Trạng thái Render "Đang dừng" & Bẫy Busy-Loop Nguồn Hết Clip

## 1. Hiện tượng & Triệu chứng
- Báo cáo định kỳ từ `farm_render_download_watchdog.py` thông báo: `Trạng thái render: ⚪ Đang dừng`.
- Trong khi đó kiểm tra tiến trình vẫn thấy `run_kibe_render_worker.py` (hoặc worker tương ứng) đang chạy ngầm (`pythonw.exe`).
- File log worker (`kibe_render_worker.log`) tăng dung lượng liên tục với các chu kỳ lặp lại chỉ cách nhau vài giây:
  `[SCAN] Tim thay 1 nick can va du dieu kien render tren Kibe.`
  `>>> [RENDER] Tik7 M31 -> Out 247 (hien co 40/45) <- Src 247 (40 clips)...`
  `  [OK] Tik7 M31 Out 247: dat 40 clips!`

## 2. Nguyên nhân gốc rễ (Root Cause)
1. **Tiến độ render farm thực chất đã xong (≥99.8%)**:
   Hầu hết tất cả các slot (Tik1..Tik8) đều đã đạt 80/80 folder ≥ 45 clip. Không còn folder nào cần render ngoại trừ 1 hoặc vài folder cá biệt.
2. **Bẫy thiếu điều kiện `src_cnt > out_cnt` (Busy-Loop)**:
   - Logic chọn task chỉ xét `out_cnt < 45` và `src_cnt >= 35`.
   - Khi folder nguồn chỉ có 40 clip và toàn bộ 40 clip đã render xong vào folder đích (`out_cnt == src_cnt == 40`), `random_batch_render.py` chạy với `--resume-verify-existing` sẽ nhận diện toàn bộ clip đã tồn tại và thoát ngay sau 1-2 giây mà không sinh thêm clip nào.
   - Worker ngay lập tức quét lại, vẫn thấy `out_cnt < 45` và `src_cnt >= 35`, tạo thành vòng lặp vô tận (busy-loop) đốt CPU.
3. **Lệch dữ liệu giữa `state.db` và đĩa thực tế**:
   - `state.db` của downloader ghi nhận `folder_num` đó có `video_count >= 45` (ví dụ 53) và trạng thái `complete` (từ lịch sử cũ trước khi dọn dẹp/xóa clip lỗi).
   - Downloader coi folder là hoàn tất nên không cào thêm video mới.
   - Trên đĩa thực tế (`D:\video goc\<id>`) chỉ còn 40 clip.
4. **Tại sao Watchdog báo "⚪ Đang dừng"**:
   - Watchdog kiểm tra xem `ffmpeg.exe` hoặc `random_batch_render.py` có đang chạy hay không.
   - Vì `ffmpeg.exe` không hề chạy (không có video mới cần render), còn `random_batch_render.py` chỉ chớp nhoáng 1s rồi tắt, nên tại thời điểm watchdog thăm dò thì không bắt được tiến trình encode -> Báo `⚪ Đang dừng`.

## 3. Quy trình chẩn đoán chuẩn (Diagnostic Runbook)
1. **Kiểm tra tiến độ tổng thể các slot Tik1..Tik8**:
   ```python
   # Đếm số folder đạt >= 45 clip trên render_root cho từng slot Tik1..Tik8
   # Nếu 7/8 hoặc 8/8 slot đã đạt 80/80 (hoặc 79/80), farm đã hoàn thành cơ bản.
   ```
2. **Liệt kê danh sách folder < 45 clip**:
   Đối chiếu `out_cnt` và `src_cnt`:
   - Nếu `out_cnt == src_cnt`: Nguồn đã cạn video mới, worker không thể render thêm.
   - Nếu `out_cnt < src_cnt`: Nguồn còn video chưa render, kiểm tra xem có bị lỗi encode / timeout không.
3. **Đối chiếu số lượng clip thực tế trên đĩa vs `state.db`**:
   Nếu trên đĩa `D:\video goc\<src_id>` có `< 45` clip nhưng trong `state.db` ghi `>= 45` và `complete`, cập nhật lại `state.db` hoặc kích hoạt downloader cào bổ sung cho niche đó.

## 4. Giải pháp khắc phục
1. **Vá logic worker & watchdog**:
   Điều kiện nhận task bắt buộc phải có:
   `if out_cnt < 45 and src_cnt >= 35 and src_cnt > out_cnt:`
   Nếu `src_cnt <= out_cnt`, coi như đã render hết nguồn, không được enqueue lại để tránh busy-loop.
2. **Bổ sung nguồn video**:
   Cào thêm tối thiểu để `src_cnt >= 45` cho folder nguồn thiếu clip.
