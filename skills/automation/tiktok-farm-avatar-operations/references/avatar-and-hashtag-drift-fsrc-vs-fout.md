# Đối Soát Avatar & Hashtag Drift: Bẫy Nhầm Lẫn Giữa F_out (Folder Render) và F_src (Folder Nguồn Gốc)

## 1. Bản Chất Sự Cố
Trên farm TikTok (1.280 tài khoản gồm 2 cụm Kibe 1..80 và Admin 201..280):
- Mỗi tài khoản chạy ở một máy `M` và một slot/Tik `Slot` (1..8).
- **Folder nguồn gốc ($F_{src}$)**: Thư mục chứa video gốc ban đầu trong `D:/video goc/`, được tính theo công thức cứng:
  $$F_{src} = (Slot - 1) \times 80 + M$$
- **Folder render/output ($F_{out}$)**: Thư mục chứa video sau render/dubbing trong `D:/TIKTOK-videonuoinick/` (cột `Folder Video` trong Excel).

## 2. Bẫy Nguy Hiểm & Dấu Hiệu Nhận Biết
1. **Lệch Avatar (Avatar Drift)**:
   - Khi tạo hoặc lấy avatar đại diện, nếu nhầm lẫn lấy từ `D:/video goc/<F_out>/avatar.jpg` thay vì `D:/video goc/<F_{src}>/avatar.jpg`, avatar sẽ bị sai lệch hoàn toàn so với nội dung video trên kênh.
   - *Ví dụ thực tế*:
     * Máy 6 Slot 5: $F_{out} = 45$, $F_{src} = (5-1)*80 + 6 = 326$. Video kênh là bé thiếu nhi Tuấn Phong/gia đình vui nhộn, nhưng folder 45 lại chứa ảnh avatar con mèo Ba Tư trắng $\rightarrow$ Kênh trẻ em hiển thị avatar con mèo!
     * Máy 63 Slot 3: $F_{out} = 499$, $F_{src} = (3-1)*80 + 63 = 223$. Video kênh là bạn nam tập gym cởi trần 6 múi, nhưng folder 499 lại chứa ảnh avatar nữ anime tóc tím $\rightarrow$ Kênh gym nam tính hiển thị avatar nữ!
2. **Lệch Niche & Hashtag (Hashtag Drift)**:
   - Tương tự, nếu bảng Excel hoặc script phân loại gán nhầm Keyword/Hashtag theo $F_{out}$ hoặc nhầm lẫn giữa dải folder, video tải lên sẽ mang hashtag rác (ví dụ video gym bị gán tag `#marketing`, video trẻ em bị gán tag `#thoitrang`).

## 3. Quy Trình Chuẩn Bị & Khắc Phục Avatar O(1)
1. **Tính toán chính xác $F_{src}$**:
   - $F_{src} = (Slot - 1) \times 80 + M$.
   - Kiểm tra các video trong `D:/video goc/<F_{src}>/` và thư mục frames `D:/video goc/<F_{src}>/.avatar_work/representative_frames/` để xác định đúng nhân vật/chủ thể chính của kênh.
2. **Crop Avatar Theo Chuẩn Invariant Của Farm**:
   - Kích thước: Chuẩn vuông `512x512` (hoặc `1080x1080`).
   - Tỷ lệ bố cục: Mặt ở khoảng 15–25% phía trên ($cy \approx 0.2 \times H$), khoảng trống đỉnh đầu (headroom) vừa đủ, **cấm cụt đầu**.
   - Kiểm tra bằng `browser_vision` tận mắt trước khi gửi hoặc upload.
3. **Đồng Bộ Hai Đầu Thư Mục**:
   - Copy file `avatar.jpg` chuẩn vào cả:
     * `D:/video goc/<F_{src}>/avatar.jpg`
     * `D:/video goc/<F_{out}>/avatar.jpg` (để mọi script dù đọc nhầm $F_{out}$ hay $F_{src}$ đều lấy đúng avatar).
4. **Khóa Bảo Vệ Tránh Script Quét Đè (SSOT Protection)**:
   - Thêm cả 2 số folder ($F_{src}$ và $F_{out}$) vào danh sách `protected_folders` và mapping `accounts` trong CẢ 2 file registry:
     * `D:/Taadaa/data/manual_avatar_protected_folders.json`
     * `D:/Taadaa/Tiktok-video/data/manual_avatar_protected_folders.json`
5. **Cập Nhật Keyword & Hashtag SoT Trong Excel**:
   - Cập nhật lại cột `Keyword Video` và `Hashtag Pool` trong `Tik<Slot>.xlsx` (sheet active) và sheet `Hashtag theo Folder` đúng với chủ đề thực tế của video kênh (ví dụ: `Gym` cho nam cơ bắp, `Chăm sóc bé` cho trẻ em/gia đình).
   - Đặt cột `Avatar` trong `Tik<Slot>.xlsx` thành `PENDING` (thay vì `OK`) để bộ lọc `resolve_avatar_pending_machines.py` nhận diện máy cần up avatar mới.
6. **Kích Hoạt Hàng Đợi Database (avatar_replace_queue)**:
   - Cập nhật SQLite `D:/Taadaa/data/tiktok_tracker.db`:
     ```sql
     UPDATE avatar_replace_queue 
     SET status = 'PENDING', video_goc = '<F_src>', folder_video = '<F_out>', last_error = NULL, updated_at = datetime('now', 'localtime')
     WHERE may = <M> AND tik = <Slot>;
     ```
   - Điều này đảm bảo khi runner batch hoặc watchdog quét qua sẽ tự động nạp avatar lên thiết bị.

## 4. Tra Cứu O(1) & Nghiệm Thu Thị Giác Tận Mắt (Gate 6 & Reverse Lookup)
1. **Tra Cứu Máy & Slot Từ Screenshot Người Dùng (Reverse Profile Lookup)**:
   - Khi người dùng gửi ảnh màn hình profile TikTok (có username/handle `@<name>`):
   - Truy vấn SQLite `D:/OneDrive/TaadaaData/tiktok_tracker.db` (hoặc `C:/Users/Kibe/iCloudDrive/Backup_OneDrive/TaadaaData/tiktok_tracker.db`):
     ```sql
     SELECT may, tik, username FROM account_mapping WHERE username LIKE '%<handle>%';
     ```
   - Đối soát số lượng video trong lưới 3x3 của ảnh với cột `Video Đã Đăng` trong `Tik<Slot>.xlsx` hoặc `taikhoan_run_safe_combined.xlsx` để chốt chặn chính xác 100% `(M, Slot)`.
   - Tính toán ngay $F_{src} = (Slot - 1) \times 80 + M$.
2. **Soi Mắt Kiểm Tra Khung Tròn Profile (Invariant LLM Soi Mắt)**:
   - Dùng `browser_navigate(url="file:///D:/video goc/<F_src>/avatar.jpg")` và `browser_vision` để trực tiếp kiểm tra ảnh đại diện có đúng là nhân vật xuất hiện trong các video trên kênh hay không.
   - Tạo ảnh mô phỏng khung tròn profile TikTok: vẽ mask hình tròn tâm `(w//2, h//2)`, bán kính $R = \min(w, h)//2$, làm tối 70% vùng nền ngoài vòng tròn.
   - Lưu ra `tmp_<name>_avatar_preview.jpg` và mở qua `browser_navigate` + `browser_vision` để xác nhận tận mắt: mặt ở trục giữa, đỉnh đầu không bị cắt, cằm và vai vừa vặn trong vòng tròn trước khi gửi thẻ `MEDIA:` cho người dùng.
3. **Kỷ Luật Dispatch Worker Khi Hết Ngân Sách T1 Coordinator**:
   - Khi Coordinator đã đạt giới hạn ghi T1 (5 files / 200 dòng): BẮT BUỘC dispatch Worker qua `delegate_task`.
   - Để tránh vi phạm `OUT OF REPO WHITELIST` (chỉ cho phép `D:/Taadaa`), không khai báo file ngoài (`D:/OneDrive/...`) vào trường `FILE:`.
   - Bọc toàn bộ thao tác đồng bộ file, cập nhật SQLite và cập nhật Excel vào một script entrypoint duy nhất trong `D:/Taadaa/tools/<script>.py`.
   - Soạn `OLD_STRING` và `NEW_STRING` trong `<<< ... >>>` với tổng dòng thay đổi `<= 30 dòng` (`DIFF_BUDGET`) để Worker vá và chạy script kiểm chứng focused.
