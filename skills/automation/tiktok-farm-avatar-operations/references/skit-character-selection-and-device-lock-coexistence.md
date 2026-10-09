# Skit Character Selection, Visual Composite Validation & Device Lock Coexistence (06/10/2026)

## 1. Sự cố thực tế ngày 06/10/2026 trên Máy 18 (@huy010822 - Tik 5)
1. **Bối cảnh:**
   - Tài khoản `@huy010822` (Máy 18 - Tik 5) làm về niche **Học sinh / Hài học đường** (Folder 141, video gốc 338).
   - Avatar đang hiển thị trên kênh là một ông chú trung niên đội nón kết leo núi ngoài trời.
   - User phản ánh: *"Ava nick này thấy sai sai đổi đi"*.

2. **Sai lầm 1 — Hiểu nhầm giữa "Kỹ thuật cắt đúng video" vs "Nghiệp vụ đúng vai nhân vật chính":**
   - Về kỹ thuật: File avatar ông chú thực chất được cắt tự động từ chính video `1.mp4` trong folder 338. Nhưng trong video đó, ông chú chỉ đóng vai phụ là phụ huynh đi đón con!
   - Về nghiệp vụ: Kênh là tiểu phẩm học đường (đồng phục áo trắng, khăn quàng đỏ, bảng lớp 7A2), việc để avatar ông chú khiến kênh trông như Facebook cá nhân, hoàn toàn lệch tông.
   - **Bài học:** Với các kênh tiểu phẩm/skit/parody, video mở đầu thường có vai khách mời/phụ huynh. CẤM TUYỆT ĐỐI chỉ lấy khuôn mặt đầu tiên của video `1.mp4`. Phải quét qua nhiều video (`2.mp4`, `4.mp4`, `8.mp4`...) để bắt đúng nhân vật trung tâm đại diện cho niche kênh (học sinh, đồng phục).

3. **Sai lầm 2 — Bẫy tạo ảnh đối chiếu bị dán trùng hình (Identical Image Trap):**
   - Agent tạo ảnh composite so sánh (`Old vs New`) nhưng sơ suất lấy nhầm cùng một file ảnh dán vào cả hai ô, trong khi text chú thích bên dưới lại ghi "Ava cũ: Ông chú" và "Ava mới: Học sinh khăn quàng đỏ".
   - User lập tức chấn chỉnh: *"Ủa gì v cùng ảnh mà? Thế ông chú đúng r à"*.
   - **Bài học:** Trước khi xuất ảnh `MEDIA:` đối chiếu, BẮT BUỘC so sánh mã băm MD5 hoặc pixel diff (`hash(img_old) != hash(img_new)`). CẤM TUYỆT ĐỐI để 2 ảnh giống hệt nhau nhưng text lại chém gió là 2 nhân vật khác nhau.

4. **Kỷ luật khi User bảo "Tự pick cái nào ổn nhất đi":**
   - Đây là lệnh ủy quyền dứt điểm: Không hỏi lại hay lưỡng lự.
   - Lập tức chọn phương án tối ưu nhất theo niche (Option 1: Nam sinh đeo kính cận, áo trắng, khăn quàng đỏ, cắt từ `4.mp4` tại 15s, căn giữa tròn).
   - Ghi đè đồng bộ cả 2 đầu kho:
     * `D:\video goc\<Folder Video>\avatar.jpg`
     * `D:\TIKTOK-videonuoinick\<Folder Video>\avatar.jpg`
   - Cập nhật bảng `avatar_replace_queue` trong `D:/Taadaa/data/tiktok_tracker.db` về `status = 'PENDING'`.

---

## 2. Kỹ thuật cùng tồn tại với Device Lock (`SKIPPED_LOCKED`)
1. **Hiện tượng:**
   - Khi kích hoạt `run_tiktok_upload_avatar.ps1` độc lập cho Máy 18, launcher ghi nhận trong `summary.csv`:
     `"18","0","3","SKIPPED_LOCKED","False","device lock active"`
   - Nguyên nhân: Máy 18 đang chạy dở ca nuôi nick chung (`PID 142344`, lệnh `run_tiktok.py --mode multi-machine-feed-session`), có tiến trình con `follow_runner.run_follow --machine 18` đang hoạt động.
2. **Kỷ luật xử lý:**
   - TUYỆT ĐỐI CẤM kill tiến trình nuôi nick của farm để giành quyền up avatar.
   - Không được spam lệnh lặp đi lặp lại khi lock đang active.
   - **Mô hình Event-Driven Chờ Nhả Lock:** Tạo script wrapper sử dụng `psutil.Process(child_pid).wait(timeout=...)` để chờ tiến trình con nhả thiết bị một cách tự nhiên, sau đó mới kích hoạt canonical runner `run_tiktok_upload_avatar.ps1` với `terminal(background=True, notify_on_complete=True)`.

---

## 3. Lỗi UnicodeDecodeError khi đọc PowerShell output trên Windows
- **Triệu chứng:** Chạy `powershell.exe` qua Python subprocess với `capture_output=True, text=True` bị văng:
  `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xad ...`
- **Nguyên nhân:** Console PowerShell trên Windows mặc định xuất mã hóa OEM (cp1258 / cp437) thay vì UTF-8.
- **Giải pháp chuẩn:** Luôn bắt byte thô (`stdout=subprocess.PIPE`) và giải mã an toàn:
  ```python
  out, err = p.communicate(input=b"RUN\r\n")
  stdout_str = out.decode("utf-8", errors="replace")
  stderr_str = err.decode("utf-8", errors="replace")
  ```

---

## 4. Sự cố Máy 71 (@phanmai0464 - Tik 8): Avatar đồ vật tĩnh bị sót do kẹt cờ DONE cũ và lệch map Excel
1. **Hiện tượng:**
   - User phản ánh: *"Acc này ava gì lạ thế? Đợt tạo ava mới fix lỗi chưa tạo cho acc này à"*.
   - Profile TikTok của nick `@phanmai0464` (Máy 71 - Tik 8) hiển thị avatar chụp cận cảnh bàn làm việc / đồ dùng học tập / cốc đỏ tĩnh (YOLO detect: 0 person).

2. **Nguyên nhân gốc rễ (Lệch tầng File vs Tầng Database Queue):**
   - **File ảnh nguồn trên đĩa:** Đã được sinh lại ảnh mới chuẩn YOLO (`person` conf=0.87) từ đêm 04/10/2026 tại `D:\video goc\568\avatar.jpg` và `D:\TIKTOK-videonuoinick\568\avatar.jpg`.
   - **Bẫy kẹt cờ DONE cũ trong DB:** Rạng sáng ngày 03/10/2026, watchdog cũ đã up ảnh góc bàn cũ và ghi nhận `status = 'DONE'` vào `avatar_replace_queue`.
   - **Lệch file map Excel khi tái tạo hàng loạt:** Script `regenerate_unique_avatars.py` đêm 04/10 đọc nhầm `taikhoan_run_safe.xlsx` (cột 1 là Device ID chuỗi hex) thay vì `taikhoan_dat_v2_updated .xlsx` (cột 1 là Folder Video), khiến script chỉ map được 8/640 folder và bỏ sót hoàn toàn việc reset `status = 'PENDING'` cho các folder còn lại trong database.
   - **Watchdog ca tối bỏ qua:** Watchdog chỉ quét các tài khoản `status == 'PENDING'`. Vì nick đã có avatar trên TikTok (`has_avatar = 1`) và trong DB queue vẫn là `DONE`, hệ thống coi là đã hoàn thành và không bao giờ tự up đè ảnh mới.

3. **Quy trình xử lý chuẩn:**
   - **Bước 1 (Reset Queue):** Cập nhật SQLite:
     ```sql
     UPDATE avatar_replace_queue
     SET status='PENDING', last_error=NULL, updated_at=datetime('now', 'localtime')
     WHERE username='phanmai0464';
     ```
   - **Bước 2 (Chạy Runner Độc lập):** Kích hoạt canonical runner qua Python byte-stream an toàn:
     `powershell.exe -File D:\Taadaa\Tiktok-video\run_tiktok_upload_avatar.ps1 -Tik 8 -ForceAvatarMachineList "71"`
   - **Bước 3 (Nghiệm thu Gate 6):**
     * Trích xuất `avatar-save-surface-guard.png` (màn crop ảnh) và `avatar-uploaded-confirmed.png` (màn Profile sau upload).
     * Kiểm tra bằng `browser_vision` để loại trừ ảnh đen / popup / lệch layout trước khi gửi `MEDIA:` cho User.
     * Cập nhật `avatar_replace_queue` về `status = 'DONE'` và kiểm tra workbook `Avatar = OK`.
