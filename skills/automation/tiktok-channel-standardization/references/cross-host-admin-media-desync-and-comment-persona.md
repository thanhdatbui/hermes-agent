# Kỷ Luật Đối Soát Media Đa Host (Admin Remote vs Controller) & Nhận Diện Persona Khán Giả

## 1. Bẫy Lệch Kho Media Đa Host (Admin-Farm vs Local Controller)
- **Thực trạng phát hiện:**
  - Đối với các máy thuộc cụm Admin (`machine >= 200`): Kho render thực tế phục vụ upload nằm tại remote host `192.168.110.119` (`D:\TIKTOK-videonuoinick-admin\<F_vid>`).
  - Kho render tại Controller cục bộ (`D:\TIKTOK-videonuoinick\<F_vid>`) có thể chứa dữ liệu cũ từ các đợt chạy trước chưa được đồng bộ (ví dụ: máy 215, Controller chứa video Thời trang ngày 07/10, trong khi máy Admin chứa video Roblox Gaming ngày 16/10).
  - Script tự động đồng bộ hàng loạt (như `sync_keywords.jsonl`) có thể ghi đè nhầm Keyword/Hashtag trong Excel `Tik<N>.xlsx` (ví dụ: đổi từ `Công nghệ` sang `Anime`), tạo ra tam giác lệch chéo: **Excel (Anime) ≠ Controller (Thời trang) ≠ Admin Thật (Roblox)**.
- **Kỷ luật điều tra O(1) chuẩn xác:**
  - Khi máy thuộc cụm Admin (`machine >= 200`), **CẤM TUYỆT ĐỐI** chỉ kiểm tra thư mục `render_local`.
  - BẮT BUỘC kiểm tra trực tiếp kho trên Admin bằng `admin_ssh.py`.
  - **Kỹ thuật chạy script remote an toàn (Base64 Exec Pattern):**
    Để tránh lỗi MSYS/git-bash làm biến dạng đường dẫn Windows (lỗi `[Errno 22] Invalid argument` do double backslash `\\\\`), Coordinator BẮT BUỘC đóng gói mã Python bằng Base64 và thực thi qua `execute_ssh_command`:
    ```python
    import base64
    from admin_ssh import execute_ssh_command

    code = "import cv2, os; ..."
    b64 = base64.b64encode(code.encode("utf-8")).decode("ascii")
    cmd = f'python -c "import base64; exec(base64.b64decode(\'{b64}\'))"'
    res = execute_ssh_command(cmd)
    ```

## 2. Nhận Diện Persona Kênh Qua Tín Hiệu Comment Khán Giả (Comment Audience Signal)
- **Quy tắc bảo toàn Human Connection:**
  - Khi video đã đăng có tương tác cao (như clip viral 22.5K views), BẮT BUỘC đọc tín hiệu từ comment khán giả để xác định định vị người sáng tạo (Persona).
  - Nếu khán giả gọi chủ kênh bằng đại từ nhân xưng giới tính rõ ràng (ví dụ: *"bả chơi bản quốc tế"* ➔ định vị là Nữ Creator / Nữ Gamer):
    * **CẤM** vội vã đổi Avatar sang hình nhân vật game 3D, hoạt hình hay logo mascot vô danh (sẽ biến kênh thành "acc bot reup game", triệt tiêu sự gắn kết con người).
    * **Ưu tiên PA 4 (Giữ nguyên Avatar Nữ thật)** hoặc nâng cấp ảnh Nữ Creator tươi tắn, đồng thời đưa chi tiết nhận diện này vào Bio để tạo sự gần gũi với khán giả.
