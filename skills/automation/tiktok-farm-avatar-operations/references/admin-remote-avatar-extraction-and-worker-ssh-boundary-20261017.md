# Admin Remote Avatar Extraction & Worker SSH Boundary (2026-10-17)

## 1. Định Vị Tọa Độ O(1) Cho Máy Admin Remote ($M \ge 200$)
- **Tra cứu DB SSOT**: Khi nhận handle TikTok (ví dụ `@huynhim41`), không quét đĩa mà tra cứu trực tiếp qua `D:/Taadaa/data/tiktok_tracker.db`:
  ```python
  import sqlite3
  conn = sqlite3.connect(r'D:\Taadaa\data\tiktok_tracker.db')
  cur = conn.cursor()
  cur.execute("SELECT username, may, tik, host_id FROM farm_account_info WHERE username='<handle>'")
  # Kết quả: ('huynhim41', 243, 5, 'admin')
  cur.execute("SELECT folder_video, video_goc FROM avatar_replace_queue WHERE username='<handle>'")
  # Kết quả: ('341', '341')
  ```
- **Công thức tính Slot & Folder Admin**:
  - Máy $M = 243$, Slot = $5$ (Tik 5).
  - $F_{src} = (Slot - 1) \times 80 + (M - 200) = 4 \times 80 + 43 = 363$.
  - $F_{vid} = ((M - 200) - 1) \times 8 + Slot = 42 \times 8 + 5 = 341$.
  - Kho video thật trên Admin-PC nằm tại: `D:\video goc may 2\341` và `D:\TIKTOK-videonuoinick-admin\341`.

---

## 2. Ranh Giới SSH & Phân Quyền Giữa Coordinator và Worker
- **Rào cản Worker Gate đối với SSH**:
  - Subagent Worker bị Worker Gate giới hạn nghiêm ngặt về toolset và terminal: chỉ được chạy `git status/diff/log`, `adb devices`, `inspect_machine.py <N>`, `pytest`, `psutil`.
  - Mọi lệnh SSH (`ssh admin-farm`, `admin_ssh.py`) do Worker gọi đều bị chặn hoặc timeout không phản hồi.
- **Quy tắc phối hợp chuẩn**:
  1. **Coordinator đảm nhiệm cầu nối SSH**: Trích xuất hoặc kéo frame ảnh thô (`f1.jpg`) từ Admin-PC về máy local Kibe (`D:/Taadaa/reports/f1.jpg`) bằng script trung gian b64 hoặc SSH.
  2. **Worker xử lý ảnh cục bộ**: Trên máy Kibe đã có đầy đủ môi trường Python, `cv2` (OpenCV), `PIL` (Pillow 12.2.0), `numpy`. Dispatch Worker thực hiện crop, căn chỉnh ngũ quan, tính headroom, vẽ viền tròn và ghép preview hoàn toàn trên máy Kibe.

---

## 3. Quy Chuẩn Contract Task EDIT Cho Worker (Tránh Bị Guard Chặn)
Khi Coordinator hết ngân sách ghi file T1 (> 5 files hoặc > 200 dòng) và cần dispatch Worker thực hiện sửa file script / tạo ảnh, prompt bắt buộc phải tuân thủ nghiêm ngặt các Gate:
1. `TASK_KIND: EDIT` (CẤM dùng `INVESTIGATE` khi cần tạo/ghi file vì INVESTIGATE ép chế độ Read-Only 100%).
2. `FILE: <đường_dẫn_tuyệt_đối>` (Scope Lock file duy nhất được phép chỉnh sửa).
3. `FOCUSED_TEST`: Bắt buộc đúng cú pháp chuẩn:
   - `python -m py_compile <file.py>` (với script công cụ / xử lý ảnh).
   - Hoặc: `python -m pytest <file.py>::<test_node> -q`.
4. `FAIL_FAST`: Bắt buộc chứa câu lệnh Gate 4:
   `FAIL_FAST: Nếu trong <= 3 iterations đầu thấy scope bất khả thi với budget 15 calls thì DỪNG NGAY (ABORT) và trả về đề xuất contract.`
