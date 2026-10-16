# Admin Remote Farm Avatar & Haar Cascade Validation Invariants

## 1. Tọa Độ & Công Thức Lưu Trữ Cụm Admin Remote ($M \ge 200$)
- **Quy tắc tính toán Index:**
  - $m_{idx} = M - 200$ (Ví dụ Máy 201 $\rightarrow m_{idx} = 1$).
  - **Kho Video Nguồn ($F_{src}$):** $F_{src} = (S - 1) \times 80 + m_{idx}$ (Ví dụ Slot 2, Máy 201: $(2-1)\times 80 + 1 = 81$).
  - **Kho Video Render ($F_{vid}$):** $F_{vid} = (m_{idx} - 1) \times 8 + S$ (Ví dụ Máy 201, Slot 2: $(1-1)\times 8 + 2 = 2$).
- **Đường dẫn trên máy Admin Remote (`admin-farm` / `192.168.110.119`):**
  - Kho video render thành phẩm: `D:\TIKTOK-videonuoinick-admin\<F_vid>`
  - Kho video nguồn gốc: `D:\video goc may 2\<F_src>`
  - Workbook quản lý slot: `D:/OneDrive/TaadaaData/admin/Tik<S>.xlsx`
  - Danh mục 640 kênh hot ngách chuẩn: `D:/OneDrive/TaadaaData/admin/admin_all_640_hot_niches.json`

## 2. Python Runtime & Kỹ Thuật Thực Thi SSH Base64 Trên Admin
- **Môi trường Python hợp lệ trên Admin:**
  - `D:/CodexRuntime/tiktok-video/venv-core024/Scripts/python.exe` (Môi trường có sẵn OpenCV `cv2`, numpy, requests).
  - Tránh dùng `D:/Taadaa/python-envs/automation/...` vì môi trường này thiếu `cv2`.
- **Mẫu thực thi an toàn qua SSH chống lỗi Quote & Null Characters:**
  ```python
  import base64, subprocess
  py_code = """
  # Python script to run on admin
  """
  b64 = base64.b64encode(py_code.encode()).decode()
  py = r"D:/CodexRuntime/tiktok-video/venv-core024/Scripts/python.exe"
  cmd = ["ssh", "-o", "BatchMode=yes", "admin-farm", f"{py} -c \"import base64; exec(base64.b64decode('{b64}').decode())\""]
  res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
  ```

## 3. Cạm Bẫy Haar Cascade Dò Nhầm Khuôn Mặt (False Positives)
- **Hiện tượng:** Bộ lọc `haarcascade_frontalface_default.xml` thường xuyên phát hiện nhầm các vật thể tròn, đĩa thức ăn xếp dưa chuột/khoai lang, hoa văn lông thú cưng hoặc họa tiết nền gạch thành khuôn mặt người với kích thước box lớn.
- **Kỷ luật kiểm chứng thị giác (Visual Verification Invariant):**
  - **TUYỆT ĐỐI CẤM** tin tưởng mù quáng vào bounding box của Haar cascade mà crop nạp ngay.
  - Bắt buộc render ảnh crop có viền tròn xanh ($512 \times 512$) và gọi `browser_vision` hoặc `ag_cli.py ask` để xác nhận tận mắt:
    1. Có đầy đủ mắt, mũi, miệng người thật.
    2. Mặt nằm cân đối chính giữa viền tròn, không bị lẹm trán/cằm.
    3. Không bị dính text, phụ đề video đè lên mặt.
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
