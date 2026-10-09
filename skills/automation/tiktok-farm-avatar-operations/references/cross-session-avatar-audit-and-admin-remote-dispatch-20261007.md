# Cross-Session Avatar Audit & Admin Remote Dispatch (2026-10-07)

## 1. Bối cảnh & Hiện tượng
Khi vận hành thay thế avatar hàng loạt trên Taadaa Farm (cả 2 cụm Kibe M1-80 và Admin M201-280):
1. Một máy thuộc cụm Admin Remote (ví dụ Máy 218 - Tik 5) cần được up avatar từ session Coordinator trên Kibe.
2. Operator thông báo: *"T cho session khác xử lý vụ ava rồi kiểm tra h ổn chưa"*.
Nếu Coordinator kết luận vội vàng dựa trên một vài log cục bộ hoặc chỉ nhìn thấy nick gần nhất thành công, hệ thống sẽ rơi vào "điểm mù": file trên đĩa vẫn trùng lặp hàng loạt và hàng nghìn nick trong hàng đợi vẫn chưa lên thiết bị.

---

## 2. Kỹ thuật Lái Runner Up Avatar Cụm Admin Remote từ Kibe
Để điều khiển thiết bị cụm Admin (`192.168.110.119:5037`) từ trạm Kibe mà không làm xung đột cấu hình cục bộ:

### Cấu hình biến môi trường & Tham số:
- **Workbook mục tiêu:** `D:\OneDrive\TaadaaData\admin\Tik<N>.xlsx`
- **Host Config:** `D:\Taadaa\machine-config\admin.yaml`
- **Environment variables bắt buộc trong sub-process:**
  ```python
  custom_env = dict(
      os.environ,
      PYTHONPATH=r"D:\Taadaa\Tiktok-video\scripts",
      ADB_SERVER_SOCKET="tcp:192.168.110.119:5037",
      TAADAA_HOST_CONFIG=r"D:\Taadaa\machine-config\admin.yaml"
  )
  ```
- **Lệnh thực thi chuẩn (Avatar-Only):**
  ```python
  cmd = [
      r"D:\Taadaa\python-envs\automation\Scripts\python.exe",
      "-m", "scripts.tiktok_workflow",
      "--config", r"D:\Taadaa\Tiktok-video\config.example.yaml",
      "--workflow-workbook", r"D:\OneDrive\TaadaaData\admin\Tik5.xlsx",
      "--machine", str(machine_id),
      "--avatar-smoke",
      "--force-avatar-upload",
      "--force-avatar-machines", str(machine_id)
  ]
  ```
- **Nguyên tắc ảnh nguồn:**
  Bắt buộc đồng bộ ảnh candidate vào cả:
  1. `D:\video goc\<Folder Video>\avatar.jpg`
  2. `D:\TIKTOK-videonuoinick\<Folder Video>\avatar.jpg`
  (Và `D:\video goc\<Video Gốc>\avatar.jpg` nếu khác số folder).

---

## 3. Quy trình Đối soát Liên Phiên (Cross-Session Audit Checklist)
Khi Operator hỏi: *"Session khác làm rồi, kiểm tra xem đã ổn chưa"*, Coordinator BẮT BUỘC thực hiện kiểm tra 2 lớp độc lập:

### Lớp 1: Kiểm toán File Ổ Đĩa (Storage Layer - MD5 Collision Audit)
- Quét toàn bộ 640 folders trong `D:\video goc` và `D:\TIKTOK-videonuoinick`.
- Gom nhóm theo MD5 hash của `avatar.jpg`.
- Kiểm tra `st_mtime` của các file trong vòng 24h qua:
  * Đếm số folder vừa được sinh lại avatar hôm nay (`now - st_mtime < 86400`).
  * Kiểm tra xem các file mới tạo hôm nay có bị trùng lặp nội bộ không.
  * Thống kê số nhóm trùng lặp còn sót lại (các folder placeholder cũ từ quá khứ chưa được quét tới).

### Lớp 2: Kiểm toán Hàng Đợi & Thiết Bị (Queue & Device Layer)
- Truy vấn bảng `avatar_replace_queue` trong `D:\Taadaa\data\tiktok_tracker.db`:
  ```sql
  SELECT host_id, status, count(*) 
  FROM avatar_replace_queue 
  GROUP BY host_id, status;
  ```
- Bóc tách rõ:
  * Số lượng tài khoản **DONE**: Đã được runner upload thành công và có ảnh verify.
  * Số lượng tài khoản **PENDING**: Đang chờ Watchdog ca tối (`post_evening_avatar_watchdog.py`) bốc ra chạy cuốn chiếu.

---

## 4. Tiêu Chuẩn Báo Cáo Cho Operator (Anti-False-Done)
- **CẤM:** Không được trả lời cụt lủn *"Ổn rồi"* chỉ vì thấy một vài acc gần nhất có status DONE.
- **BẮT BUỘC:** Báo cáo tách bạch 2 phần:
  1. **Đã đạt được (Phần ổn):** Pipeline sinh ảnh mới hoạt động chuẩn (độ độc bản cao, không trùng trong batch mới), đã up thành công bao nhiêu nick lên thiết bị.
  2. **Tồn đọng cần xử lý (Phần chưa ổn):** Còn bao nhiêu nhóm folder cũ trên đĩa chưa được chạm tới để sinh lại khung hình, và còn bao nhiêu nick đang nằm chờ trong queue PENDING.

---

## 5. Chiến Lược Tiếp Quản Khi Session Trước Dừng Dở Dang (Handoff Takeover Strategy)
Khi Operator thông báo: *"Session kia dừng rồi. Giờ mày quét nốt hay sao"*:
1. **Phân loại tệp mục tiêu (Target Filtering O(1)):**
   - Không quét lại toàn bộ 640 folder để tránh ghi đè các avatar đã chuẩn.
   - Lọc ra danh sách folder:
     * Nằm trong các nhóm trùng lặp MD5 còn sót lại (`len(dup_group) > 1`).
     * `st_mtime` cũ (không thuộc batch mới sinh trong 24h qua).
     * **Bắt buộc kiểm tra video tồn tại:** Dùng `os.path.isfile(os.path.join(fdir, '1.mp4'))` (chạy <0.01s, cấm dùng `glob('*.mp4')` gây timeout 45s).
2. **Tách riêng folder rỗng (`NO_VIDEOS`):**
   - Những folder chưa có clip nguồn (ví dụ 42 folders rỗng) phải tách riêng sang danh sách chờ tải nguồn Niche Hot mới, tuyệt đối không đưa vào tiến trình sinh avatar tránh báo lỗi crash hàng loạt.
3. **Quy trình 2-Pass xử lý dứt điểm khi gặp Timeout / Duplicate:**
   - **Pass 1 (Đa luồng 8 Workers):** Dùng `regenerate_unique_avatars.py` gọi `_make_avatar.py` chạy cho toàn bộ folder trùng.
   - **Bẫy Timeout (>180s):** Các folder chứa nhiều video dung lượng lớn hoặc video dài rất dễ bị `_make_avatar.py` quét Haar/YOLO quá 180s dẫn đến Timeout trong ThreadPool.
   - **Pass 2 (Targeted Fast FFmpeg Fallback):**
     * Với các cặp trùng/timeout còn sót lại, trích xuất tức thì (<1s) bằng FFmpeg trực tiếp từ clip đầu tiên `1.mp4`:
       ```bash
       ffmpeg -hide_banner -loglevel error -y -ss 00:00:03.500 -i "1.mp4" -vf "crop='min(iw,ih)':'min(iw,ih)',scale=512:512" -vframes 1 -q:v 2 "avatar.jpg"
       ```
     * **Bẫy clip siêu ngắn (Short-clip duration < 3.5s):** Nếu video ngắn hơn 3.5s (ví dụ folder 262 clip chỉ dài 2.66s), lệnh seek ở `00:00:03.500` sẽ bị lỗi hoặc không tạo ảnh mới, làm giữ nguyên hash trùng cũ! Bắt buộc kiểm tra hoặc seek ở timestamp an toàn (ví dụ `00:00:01.000`).
   - **Đồng bộ 2 đầu kho Kibe:** Bắt buộc đồng bộ file `avatar.jpg` vào cả `D:\video goc` và `D:\TIKTOK-videonuoinick`, đối soát MD5 đạt **640/640 folder độc bản (0 nhóm trùng lặp)**.
   - **Đồng bộ Database sang Admin Farm:**
     * Watchdog trên máy Admin (`post_evening_avatar_watchdog.py`) mặc định đọc database tại `D:\Taadaa\data\tiktok_tracker.db`.
     * Nếu thư mục `D:\Taadaa\data` trên Admin chưa tồn tại, bắt buộc tạo thư mục và `scp D:/Taadaa/data/tiktok_tracker.db admin-farm:D:/Taadaa/data/tiktok_tracker.db` để Watchdog ca tối trên Admin nhận diện đúng danh sách PENDING cần up.


