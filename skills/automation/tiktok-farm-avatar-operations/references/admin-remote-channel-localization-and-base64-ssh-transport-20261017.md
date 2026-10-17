# Admin Remote Channel Localization & Base64 Transport via SSH (2026-10-17)

## 1. Định Vị Tọa Độ Kênh Admin Remote (M >= 201) Qua Database SSOT
Khi nhận screenshot profile kênh cần chuẩn hoá (ví dụ `@huynhim41`):
1. **Tra cứu $O(1)$ trong SQLite SSOT**:
   - `D:/Taadaa/data/tiktok_tracker.db` chứa các bảng: `farm_account_info`, `avatar_replace_queue`, `snapshots`.
   - Tra cứu username:
     ```python
     import sqlite3
     conn = sqlite3.connect(r'D:\Taadaa\data\tiktok_tracker.db')
     cur = conn.cursor()
     cur.execute("SELECT * FROM farm_account_info WHERE username='huynhim41'")
     # Trả về: ('huynhim41', 243, 5, ..., 'admin') -> Máy 243, Slot 5, host Admin
     ```
2. **Cơ chế Mapping Kênh & Kho Admin Remote**:
   - Máy Admin Remote: $M \ge 201$.
   - Công thức kho video:
     - Nguồn cào: $F_{src} = (Slot - 1) \times 80 + (M - 200)$
     - Render nuôi: $F_{vid} = ((M - 200) - 1) \times 8 + Slot$
   - Lưu ý quan trọng: Trong `avatar_replace_queue`, kiểm tra chính xác `folder_video` và `video_goc` (ví dụ: máy 243 slot 5 thực tế trỏ kho 341 trên Admin-PC: `D:/video goc may 2/341/` và `D:/TIKTOK-videonuoinick-admin/341/`).

## 2. Kỹ Thuật Base64 Payload Transport Qua SSH
Khi gọi SSH sang Admin-farm (`admin-farm` / `192.168.110.119`):
1. **Bẫy Encode/Decode Console & Special Characters**:
   - Tránh truyền code Python phức tạp trực tiếp trên command-line SSH vì dễ bị lỗi escaping (`SyntaxError`) hoặc bảng mã Windows ANSI/CP1252 (`UnicodeDecodeError` / `charmap` error).
2. **Kỹ thuật đóng gói Base64 tiêu chuẩn**:
   - Encode toàn bộ script Python thành chuỗi Base64 ở máy Coordinator:
     ```python
     import base64, subprocess
     py_code = """
     import cv2, os
     # logic xử lý OpenCV trên venv-core024
     """
     b64 = base64.b64encode(py_code.encode()).decode()
     py_remote = r"D:/CodexRuntime/tiktok-video/venv-core024/Scripts/python.exe"
     ssh_cmd = ["ssh", "-o", "BatchMode=yes", "admin-farm", f"{py_remote} -c \"import base64; exec(base64.b64decode('{b64}').decode())\""]
     res = subprocess.run(ssh_cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
     ```
3. **Kéo File Ảnh Binary Từ Admin-farm Về Kibe**:
   - Đọc file binary remote, base64 encode qua stdout:
     ```python
     py_code = "import base64, sys; data = open(sys.argv[1], 'rb').read(); sys.stdout.buffer.write(base64.b64encode(data))"
     cmd = ["ssh", "-o", "BatchMode=yes", "admin-farm", f"python -c \"{py_code}\" \"{remote_path}\""]
     res = subprocess.run(cmd, capture_output=True, check=True)
     # Lọc bỏ các dòng banner SSH (Warning / **)
     clean_lines = [l for l in res.stdout.splitlines() if not l.startswith(b"Warning") and not l.startswith(b"**")]
     raw = base64.b64decode(b"".join(clean_lines))
     with open(local_path, "wb") as f:
         f.write(raw)
     ```
