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
   - Thêm cả 2 số folder ($F_{src}$ và $F_{out}$) vào `D:/Taadaa/data/manual_avatar_protected_folders.json` (danh sách `protected_folders` và mapping `accounts`).
5. **Cập Nhật Keyword & Hashtag SoT Trong Excel**:
   - Cập nhật lại cột `Keyword Video` và `Hashtag Pool` trong `Tik<Slot>.xlsx` và `Hashtag theo Folder` đúng với chủ đề thực tế của video kênh (ví dụ: `Gym` cho nam cơ bắp, `Chăm sóc bé` cho trẻ em/gia đình).
