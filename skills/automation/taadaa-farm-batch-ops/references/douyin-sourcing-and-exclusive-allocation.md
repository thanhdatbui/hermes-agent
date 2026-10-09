# Douyin Video Sourcing & Two-Tier Exclusive Allocation Runbook

## 1. Nguyên Tắc & Quy Chuẩn (User Invariants)
- **Tự động hóa 100% tiếng Trung**: User không biết tiếng Trung, cấm tiệt việc yêu cầu user tìm link/profile Douyin. Hệ thống tự động trích xuất profile từ Douyin sitemap (`hotauthor_0_1`) hoặc search tags.
- **Thư mục lưu trữ**: Tuyệt đối cấm tải video dung lượng lớn vào ổ `C:\`. Luôn dùng `D:\video goc\` (nguồn) và `D:\TIKTOK-videonuoinick\` (render).
- **Phân bổ 2 tầng (Two-Tier Allocation)**:
  - **Độc quyền (Exclusive)**: Quét từng creator, nếu creator có $\ge 40$ clip đạt chuẩn AI $\rightarrow$ gán độc quyền cho 1 folder duy nhất (lấy tối đa 40-45 clip). Kênh mang tính nhận diện cá nhân 1 khuôn mặt.
  - **Gom thừa về Bể Gộp (Curated Pool)**:
    - Nếu creator độc quyền có $> 40$ clip: Clip thừa từ số 41 trở đi gom đẩy vào `D:\video goc\curated_pool`.
    - Nếu creator không đủ 40 clip: Dồn toàn bộ clip đạt chuẩn vào `curated_pool`.
    - Thư mục `curated_pool` dùng làm nguồn bù cho các folder tạp chí đa kênh xoay vòng.

## 2. Kỹ Thuật f2 & Vượt Lỗi Thực Chiến
- **Tắt Bark Notification**: Trong `f2/conf/conf.yaml`, bắt buộc đặt `enable_bark: false` để tránh timeout 30s mỗi request tải.
- **Quy tắc đặt tên file (Naming Convention)**:
  - Trong `f2/conf/app.yaml`, Douyin naming mặc định là `{create}_{desc}`. Nếu tiêu đề chứa ký tự tiếng Trung quá dài hoặc icon emoji sẽ gây lỗi Windows Path / MAX_PATH hoặc không đọc được.
  - Sửa thành: `naming: '{create}_{aweme_id}'` để tên file ngắn gọn, duy nhất và an toàn trên Windows.
- **Bắt file tải về an toàn**:
  - `f2` lưu file theo cấu trúc: `<output_dir>/douyin/post/<Tên_Author>/<file.mp4>`.
  - Cấm dùng `rglob('*.mp4')` quét diện rộng vì dính guard an toàn. Dùng duyệt trực tiếp thư mục `post_dir = c_temp / 'douyin' / 'post'` rồi duyệt qua các subfolder tác giả.

## 3. Bộ Lọc 2 Tầng AI Cho Douyin
- **Blacklist từ khóa rác**: Lọc triệt để tên file/title chứa `动漫`, `二次元`, `漫剧`, `游戏`, `段子`, `萌宠`, `粘土`, `手工`, `bjd`, `排球`, `假吃`, `cos`, `cosplay`...
- **AI Vision ViT ONNX**: Ngưỡng `score >= 0.70` (ưu tiên $\ge 0.75$) để lọc chuẩn bạn nữ người thật, loại bỏ hoạt hình 3D, nam giới, đồ vật.
- **AI Whisper**: Chạy Whisper CPU int8 quét âm thanh. Phát hiện `zh` speech $\ge 0.60$ $\rightarrow$ REJECT. Chỉ chấp nhận `no_speech` (thuần nhạc nền BGM/dance remix).

## 4. Mở Rộng Sang Dàn Admin (SSH)
- Khi mở rộng sang máy Admin (`admin-farm` / `192.168.110.119`):
  - Đồng bộ script, manifest, proxy pool và model ONNX sang Admin qua `scp`.
  - Kiểm tra môi trường: Admin cần cài `numpy`, `onnxruntime`, `Pillow`, `yt-dlp`.
  - Biến môi trường bắt buộc: `$env:PYTHONUTF8='1'` để tránh lỗi `charmap` codec của Python trên Windows.
  - Chạy ngầm qua script `.bat` hoặc PowerShell `Start-Process` để giải phóng session SSH.
