# Admin Cluster Remote Avatar Operations & Channel Source Audit

## 1. Remote Python Runtime on Admin Host (`192.168.110.119`)
Khi thao tác trích xuất frame, xử lý ảnh (OpenCV `cv2`, `numpy`) từ xa trên cụm Admin qua SSH (`admin_ssh.py` hoặc PowerShell SSH):
- **BẪY (PITFALL):** Tuyệt đối **KHÔNG** dùng `D:/Taadaa/python-envs/automation/Scripts/python.exe` trên Admin. Môi trường này chỉ có automation core nhẹ, **KHÔNG CÓ `cv2`**, sẽ crash ngay với lỗi `ModuleNotFoundError: No module named 'cv2'`.
- **ĐÚNG (CANONICAL):** Bắt buộc dùng runtime đầy đủ của video pipeline:
  ```text
  D:/CodexRuntime/tiktok-video/venv-core024/Scripts/python.exe
  ```
  Runtime này tích hợp sẵn OpenCV 4.x, NumPy, PIL, hỗ trợ `cv2.VideoCapture` đọc video trực tiếp từ kho `D:/TIKTOK-videonuoinick-admin/<F_vid>/`.

## 2. Công thức ánh xạ Folder cụm Admin ($M \ge 201$)
Để tránh nhầm lẫn giữa kho nguồn gốc ($F_{src}$) và kho render thành phẩm ($F_{vid}$):
- Chỉ số máy cục bộ: $m_{idx} = M - 200$ (Ví dụ: Máy 201 $\rightarrow m_{idx} = 1$; Máy 218 $\rightarrow m_{idx} = 18$).
- Với Slot $S \in [1, 8]$:
  - **Kho nguồn gốc ($F_{src}$):** $F_{src} = (S - 1) \times 80 + m_{idx}$
    - Ví dụ: Máy 201, Slot 2: $(2 - 1) \times 80 + 1 = 81$ (Thư mục: `D:/video goc may 2/81` hoặc `D:/video goc/81`).
  - **Kho render ($F_{vid}$):** $F_{vid} = (m_{idx} - 1) \times 8 + S$
    - Ví dụ: Máy 201, Slot 2: $(1 - 1) \times 8 + 2 = 2$ (Thư mục: `D:/TIKTOK-videonuoinick-admin/2`).

## 3. Tra cứu Kênh Nguồn ("Kênh Hot" Channel Source Audit)
Khi cần xác minh kho video tải về thuộc kênh nào, có phải kênh hot / viral không:
- Tra cứu nhanh trong file master CSDL của Admin:
  `D:/Taadaa/data/admin_real_folders.json`
- Cấu trúc bản ghi: `[folder_id, niche, video_count, status, channel_url]`
- Từ `channel_url` (YouTube Channel ID / Handle), đối soát tên kênh và lượng người theo dõi:
  - Ví dụ Folder 2: `https://www.youtube.com/channel/UCR81BPgPCC3vSjio40ZqElQ` $\rightarrow$ Kênh **Lão Cò Video** (>138k subs, chuyên vlog ăn uống dân dã, giảm cân, sinh hoạt).
  - Ví dụ Folder 81: `https://www.youtube.com/channel/UC4kNtS0bVpDOMZ85H9vLywA` $\rightarrow$ Kênh **HÀ NỘI ĂN GÌ !** (ẩm thực đường phố).
- Xác minh này giúp đối soát chính xác Niche trong `Tik*.xlsx` (tránh tình trạng file ghi Ẩm thực nhưng video bị gán nhầm hoặc ngược lại).

## 4. Kỷ luật Ghim Video (Pin Top Invariant)
- **Ngưỡng ghim:** Chỉ ghim video khi $\ge 1.000$ views (tối đa 3 video).
- **Fail-Closed:** Nếu tất cả video đã đăng đều $< 1.000$ views (ví dụ 59, 90, 105, 387 views), **BẮT BUỘC giữ nguyên, không ghim bừa bãi**. Báo cáo rõ view thực tế cho User.

## 5. Khóa Marker Chống Đè Trên Admin
Sau khi cập nhật avatar sạch và chốt hashtag cho kho $F_{vid}$:
- Tạo ngay 2 marker bảo vệ trong thư mục render trên Admin:
  ```text
  D:/TIKTOK-videonuoinick-admin/<F_vid>/.manual_avatar_locked
  D:/TIKTOK-videonuoinick-admin/<F_vid>/.manual_hashtag_locked
  ```
- Việc này ngăn chặn cron upload hoặc nurture tự động ghi đè hoặc đổi ngẫu nhiên avatar/hashtag trong các ca chạy sau.
