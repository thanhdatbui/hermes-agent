# Cross-Farm Avatar Isolation & Admin Video Goc May 2 (2026-10-10)

## 1. Bối cảnh & Cảnh báo Nghiêm trọng (P0 Operator Correction)
- **Cảnh báo từ Operator**: *"Là sao? Tự nhiên lấy của kibe ném qua admin!!?"*
- **Sai lầm ngộ nhận**: Khi Operator bảo *"Làm cả admin"* hoặc *"Chuẩn hoá admin"*, agent thấy `D:\TIKTOK-videonuoinick-admin` thiếu avatar nên vội vàng nén toàn bộ avatar từ Kibe (`D:\TIKTOK-videonuoinick`) ném sang Admin.
- **Hậu quả**: Ô nhiễm chéo ngách trên diện rộng! Kibe và Admin vận hành 2 tập tài khoản và 2 kho video độc lập hoàn toàn:
  - **Kibe (Máy 1–80)**: Kho video thô `D:\video goc`, kho render `D:\TIKTOK-videonuoinick`. Ví dụ Folder 1: thanh niên đeo kính râm ôm mèo hài hước.
  - **Admin (Máy 201–280)**: Kho video thô `D:\video goc may 2`, kho render `D:\TIKTOK-videonuoinick-admin`. Ví dụ Folder 1: bé gái học sinh tiểu học áo trắng cổ xanh.
  - Đè avatar Kibe sang Admin làm toàn bộ tài khoản Admin bị gán sai nhân vật và lệch ngách video đăng bài.

---

## 2. Quy tắc Bất biến: Cách ly Media 2 Trạm (Cross-Farm Isolation)
1. **CẤM TUYỆT ĐỐI copy file avatar hoặc video giữa Kibe và Admin** trừ khi đó là tác vụ cào/render mới được chỉ định rõ ràng.
2. Khi chuẩn hoá avatar cho Admin:
   - **Nguồn avatar của Admin**: BẮT BUỘC trích xuất 100% từ `D:\video goc may 2` của Admin.
   - **Đích media của Admin**: BẮT BUỘC lưu vào `D:\TIKTOK-videonuoinick-admin`.
3. Kiểm tra Python Runtime trên Admin:
   - Python hệ thống (`C:\Users\Admin\AppData\Local\Programs\Python\...`) KHÔNG có `cv2` (`ModuleNotFoundError: No module named 'cv2'`).
   - BẮT BUỘC chạy trích xuất avatar bằng Python venv đã cài sẵn OpenCV:
     `D:\CodexRuntime\tiktok-video\venv-core024\Scripts\python.exe D:\Taadaa\Tiktok-video\scripts\_make_avatar.py <folder> --source-root "D:\video goc may 2"`

---

## 3. Quy trình Chuẩn hoá Avatar Admin khi nhận lệnh "Làm cả admin"
1. **Kiểm tra đường dẫn**:
   - Xác nhận `config-admin.yaml`: `avatar_source_root: D:\TIKTOK-videonuoinick-admin`.
   - Xác nhận `_make_avatar.py` tự động nhận diện `DEFAULT_SOURCE_ROOT = D:\video goc may 2`.
2. **Khóa công thức Excel & SQLite**:
   - Đồng bộ `video_goc = folder_video` trong `admin/Tik1..8.xlsx` và `avatar_replace_queue`.
3. **Trích xuất cục bộ từ video gốc máy 2**:
   - Quét các folder trong `D:\video goc may 2` thiếu avatar.
   - Dùng venv-core024 trích xuất avatar từ chính video trong folder đó của Admin.
   - Đồng bộ sang `D:\TIKTOK-videonuoinick-admin`.
4. **Phục hồi khẩn cấp nếu lỡ dính contamination**:
   - Sao chép đè toàn bộ `avatar.jpg` từ `D:\video goc may 2` sang `D:\TIKTOK-videonuoinick-admin`.
   - Xóa các avatar rác không có nguồn trong `video goc may 2`.
