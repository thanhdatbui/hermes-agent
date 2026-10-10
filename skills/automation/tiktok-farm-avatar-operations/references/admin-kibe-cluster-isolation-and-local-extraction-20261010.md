# Admin vs Kibe Cluster Isolation & Local Extraction (2026-10-10)

## 1. Sự cố Phẫn nộ từ Operator: Bẫy Copy Avatar Kibe sang Admin
Khi Operator bảo *"Làm cả admin"*, Coordinator ngộ nhận rằng toàn farm dùng chung video pool và copy avatar từ Kibe sang Admin. Operator phản ứng gay gắt: *"Là sao? Tự nhiên lấy của kibe ném qua admin!!? Ý tao là kiểm tra bên admin trích xuất chuẩn đường dẫn chưa"*.

## 2. Bản chất Độc lập Tuyệt đối giữa 2 Cụm (Cluster Isolation)
Hai trạm vận hành 2 nguồn video và media hoàn toàn riêng biệt:
- **Cụm Kibe (Máy 1–80)**:
  - Video gốc raw: `D:\video goc`
  - Video render & Avatar nuôi: `D:\TIKTOK-videonuoinick`
- **Cụm Admin (Máy 201–280 / admin-farm)**:
  - Video gốc raw: `D:\video goc may 2` (259 folders)
  - Video render & Avatar nuôi: `D:\TIKTOK-videonuoinick-admin` (640 folders)
  - Cấu hình: `config-admin.yaml` (`avatar_source_root: D:\TIKTOK-videonuoinick-admin`)

## 3. Nguy cơ Ô nhiễm Chéo Ngách (Cross-Cluster Contamination)
- Cùng một số folder (ví dụ Folder 1):
  - Kibe là kênh giải trí meme/reaction (thanh niên đeo kính râm ôm mèo).
  - Admin là kênh đời sống học đường/vlog (bé gái học sinh tiểu học áo trắng cổ xanh).
- Việc copy avatar từ Kibe sang Admin làm toàn bộ tài khoản Admin bị đổi sang hình ảnh không khớp với nội dung video thực tế đăng tải.

## 4. Quy trình Trích xuất Chuẩn hoá cho Cụm Admin
1. **Kiểm tra đường dẫn cấu hình trên Admin**:
   - `config-admin.yaml` trỏ `avatar_source_root: D:\TIKTOK-videonuoinick-admin`.
   - `scripts/tiktok_workflow/path_resolver.py` ưu tiên `D:\video goc may 2` và fallback `D:\TIKTOK-videonuoinick-admin`.
2. **Trích xuất cục bộ từ nguồn máy 2**:
   - Chạy lệnh trích xuất trực tiếp trên máy chủ Admin từ `D:\video goc may 2\<folder>`:
     ```bash
     D:\CodexRuntime\tiktok-video\venv-core024\Scripts\python.exe D:\Taadaa\Tiktok-video\scripts\_make_avatar.py <folder> --source-root "D:\video goc may 2"
     ```
   - **Bắt buộc dùng `venv-core024`**: Python hệ thống của Admin thiếu thư viện `cv2`. Chỉ có `D:\CodexRuntime\tiktok-video\venv-core024\Scripts\python.exe` có sẵn `cv2 4.11.0` và `ultralytics`.
3. **Đồng bộ nội bộ Admin**:
   - Sao chép avatar vừa sinh vào cả 2 đầu kho nội bộ của Admin:
     - `D:\video goc may 2\<folder>\avatar.jpg`
     - `D:\TIKTOK-videonuoinick-admin\<folder>\avatar.jpg`
   - TUYỆT ĐỐI CẤM can thiệp hay sao chép chéo giữa Kibe và Admin.
