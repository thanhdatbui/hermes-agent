# Kỷ Luật Tạo Avatar Độc Bản & Quét Trùng Toàn Diện Trên Phone Farm

## 1. Bản chất sự cố (04/10/2026)
- **Sự cố báo cáo sai**: Phiên làm việc báo cáo toàn farm "đã hết trùng avatar", nhưng thực tế tài khoản Thúy Vũ (`.thy.v5`, Folder 148, Máy 19) bị User phát hiện trùng y hệt avatar với 3 tài khoản khác (Máy 4 Folder 25, Máy 25 Folder 193, Máy 33 Folder 259).
- **Nguyên nhân gốc (Root Cause)**:
  1. **Quét nông bằng danh sách cứng (`FOLDERS_DUP`)**: Script `regenerate_unique_avatars.py` chỉ lặp qua danh sách cứng ~40 folder nghi vấn thay vì tính hash MD5/SHA256 trên toàn bộ các folder trong kho `D:\TIKTOK-videonuoinick`. Cụm 4 folder `[25, 148, 193, 259]` nằm ngoài danh sách cứng nên bị bỏ lọt hoàn toàn, tạo ra kết quả kiểm tra giả mạo (False Clean).
  2. **Vi phạm nguyên tắc nguồn ảnh độc bản**: Khi thiếu avatar hoặc xử lý hàng loạt, hệ thống cũ đã copy trùng file ảnh giữa các folder thay vì tạo độc bản từ video gốc của từng folder.

## 2. Quy tắc bắt buộc khi tạo & kiểm tra Avatar Farm

### A. Nguyên tắc tạo avatar độc bản
- **Mỗi folder là một tài sản độc lập**: Avatar của folder $N$ **BẮT BUỘC** phải được tạo từ chính video trong folder $N$ (`D:\video goc\<N>` hoặc `D:\TIKTOK-videonuoinick\<N>`).
- **CẤM TUYỆT ĐỐI**: Copy `avatar.jpg` từ folder này sang folder khác để chữa cháy hoặc lấp đầy chỗ trống.
- **Công cụ chuẩn**: Sử dụng canonical script trích xuất frame đại diện:
  ```bash
  python D:/Taadaa/Tiktok-video/scripts/_make_avatar.py <folder_number> --output D:/video goc/<folder>/avatar.jpg
  ```
  Script tự động dùng mô hình YOLOv8 (`yolov8n.pt`) nhận diện chủ thể/khuôn mặt trong video, crop vuông tỷ lệ 1:1, nếu không nhận diện được sẽ fallback lấy frame đầu tiên của video gốc.

### B. Quy tắc quét trùng avatar (Anti-False Clean)
- **CẤM kiểm tra theo whitelist/danh sách cứng**: Mọi kết luận "không còn trùng avatar" chỉ hợp lệ khi được chứng minh bằng kết quả quét hash MD5/SHA256 toàn diện:
  1. Duyệt toàn bộ `*/avatar.jpg` trong cả hai kho: `D:\TIKTOK-videonuoinick\` và `D:\video goc\`.
  2. Nhóm theo hash file (`hashlib.md5(p.read_bytes()).hexdigest()`).
  3. Chỉ kết luận SẠCH khi `len(matching_folders) == 1` cho tất cả các hash.
- **Quy trình tái tạo khi phát hiện trùng**:
  Khi phát hiện folder $N$ có hash trùng với folder khác:
  1. Chạy `_make_avatar.py N` để sinh lại avatar mới từ video gốc của folder $N$.
  2. Đồng bộ đè sang cả hai nơi: `D:\video goc\<N>\avatar.jpg` và `D:\TIKTOK-videonuoinick\<N>\avatar.jpg`.
  3. Kích hoạt runner chuẩn `run_tiktok_upload_avatar.ps1 -Tik <T> -ForceAvatarMachineList <M>` với cờ force để đẩy đè lên app TikTok của máy thật.

### C. Kỷ luật hành động theo lệnh User (Chống hỏi lặp lại)
- Khi User đã ra chỉ thị rõ ràng ("chạy cho tao", "làm đi"):
  - **CẤM TUYỆT ĐỐI** dùng công cụ `clarify` để hỏi lại "có nên chạy không", "chạy theo cách nào".
  - Bắt buộc kích hoạt ngay lập tức qua runner nền chuẩn, giám sát tiến trình và nghiệm thu bằng ảnh chụp thực tế (`MEDIA:`).
