# Admin Remote Avatar & Media Management Invariants

## 1. Tọa Độ & Công Thức Tính Kho Cụm Admin Remote ($M \ge 200$)
- **Chỉ số máy cục bộ:** $m_{idx} = M - 200$ (Ví dụ Máy 201 $\rightarrow m_{idx} = 1$).
- **Kho Video Nguồn Gốc ($F_{src}$):** $F_{src} = (S - 1) \times 80 + m_{idx}$
  - *Ví dụ:* Máy 201, Slot 2: $(2 - 1) \times 80 + 1 = 81$ (`D:\video goc may 2\81`).
- **Kho Video Render Thành Phẩm ($F_{vid}$):** $F_{vid} = (m_{idx} - 1) \times 8 + S$
  - *Ví dụ:* Máy 201, Slot 2: $(1 - 1) \times 8 + 2 = 2$ (`D:\TIKTOK-videonuoinick-admin\2`).
- **Danh mục Niche Hot:** `D:/OneDrive/TaadaaData/admin/admin_all_640_hot_niches.json` và `admin_real_folders.json`.

## 2. Python Runtime Hợp Lệ Trên Admin Remote (`admin-farm`)
- **Môi trường Python:** `D:/CodexRuntime/tiktok-video/venv-core024/Scripts/python.exe`. Môi trường này tích hợp sẵn OpenCV (`cv2`), `numpy`, `requests`.
- **Lưu ý:** `D:/Taadaa/python-envs/automation/Scripts/python.exe` thiếu `cv2` $\rightarrow$ không được dùng cho tác vụ xử lý hình ảnh/video.
- **Mẫu thực thi lệnh SSH Base64 an toàn (tránh lỗi nháy kép và ký tự null):**
  ```python
  import base64, subprocess
  code = '''
  # Python code to execute on admin-farm
  '''
  b64 = base64.b64encode(code.encode()).decode()
  py = r"D:/CodexRuntime/tiktok-video/venv-core024/Scripts/python.exe"
  cmd = ["ssh", "-o", "BatchMode=yes", "admin-farm", f"{py} -c \"import base64; exec(base64.b64decode('{b64}').decode())\""]
  res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
  ```

## 3. Cạm Bẫy Haar Cascade Dò Nhầm Khuôn Mặt (False Positives)
- **Hiện tượng:** Bộ lọc `haarcascade_frontalface_default.xml` thường xuyên nhận diện nhầm các vật thể tròn, đĩa thức ăn (dưa chuột, khoai lang, đĩa đồ ăn tròn), hoa văn lông thú cưng hoặc nền gạch sỏi thành khuôn mặt người với diện tích box lớn.
- **Kỷ luật kiểm chứng thị giác (Visual Verification Invariant):**
  - **CẤM TUYỆT ĐỐI** tin tưởng mù quáng vào bounding box của Haar cascade mà nạp ngay lên profile.
  - Bắt buộc render ảnh crop có viền tròn xanh ($512 \times 512$) và gọi `browser_vision` hoặc `ag_cli.py ask` để soi mắt kiểm tra trước khi gửi hoặc nạp.
- **Phương án dự phòng khi video không có khuôn mặt quay trực diện:**
  - Kiểm tra `avatar.jpg` tại kho video gốc: `D:/video goc/<F_src>/avatar.jpg` hoặc `D:/video goc may 2/<F_src>/avatar.jpg`.
  - Hoặc trích xuất avatar chính thức từ URL kênh YouTube/TikTok gốc được quản lý trong `admin_real_folders.json`.

## 4. Quy Trình Khóa 2 Tầng (Lock Markers & Protection Manifests)
- **Tầng 1 (File Markers vật lý):** Tạo file `.manual_avatar_locked` và `.manual_hashtag_locked` tại cả 2 thư mục:
  - `D:\TIKTOK-videonuoinick-admin\<F_vid>`
  - `D:\video goc may 2\<F_src>`
- **Tầng 2 (JSON Registry bảo vệ):** Bổ sung cả $F_{vid}$ và $F_{src}$ vào danh sách `protected_folders` trong:
  - `D:/Taadaa/data/manual_avatar_protected_folders.json`
  - `D:/Taadaa/data/manual_hashtag_protected_folders.json`
