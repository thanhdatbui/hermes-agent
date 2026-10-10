# Cross-Cluster Avatar Isolation & Admin Pipeline Audit (2026-10-10)

## 1. Bối cảnh & Sai lầm Ngộ nhận Nghiêm trọng
Khi Operator yêu cầu: *"Làm cả admin"*:
- **Sai lầm chết người của Agent**: Tự ý nén toàn bộ 640 avatar từ trạm Kibe (`D:\TIKTOK-videonuoinick`) thành file tar rồi SCP giải nén đè vào trạm Admin (`D:\TIKTOK-videonuoinick-admin`).
- **Phản ứng gắt từ Operator**: *"Là sao? Tự nhiên lấy của kibe ném qua admin!!?"* - *"Chứ gì nx? Ý tao là kiểm tra bên admin trích xuất chuẩn đường dẫn chưa"*.

---

## 2. Bản chất Độc lập Tuyệt đối giữa 2 Kho Video
Kibe và Admin là hai thực thể hạ tầng nuôi nick riêng biệt, sử dụng hai nguồn video hoàn toàn khác nhau:

| Tiêu chí | Trạm Kibe (Máy 1–80) | Trạm Admin (Máy 201–280) |
|---|---|---|
| Kho video gốc (Raw) | `D:\video goc` | `D:\video goc may 2` |
| Kho video nuôi (Render SSOT) | `D:\TIKTOK-videonuoinick` | `D:\TIKTOK-videonuoinick-admin` |
| Workbook sổ cái | `D:\OneDrive\TaadaaData\kibe\Tik1..8.xlsx` | `D:\OneDrive\TaadaaData\admin\Tik1..8.xlsx` |
| Ví dụ Folder 1 | Reaction thanh niên kính râm ôm mèo | Nữ sinh tiểu học áo trắng cổ xanh trường Long Hòa |

Việc lấy avatar của Kibe chép sang Admin gây **ô nhiễm chéo ngách toàn diện (Cross-Cluster Contamination)**: nick trên Admin đăng video một đằng nhưng avatar lại hiển thị nhân vật từ video của máy Kibe.

---

## 3. Quy trình Kiểm tra Chuẩn hóa trên Admin ("Làm cả admin")

Khi Operator ra lệnh *"Làm cả admin"* trong bài toán avatar, quy trình BẮT BUỘC gồm 4 bước kiểm toán hạ tầng, KHÔNG copy ảnh:

### Bước 1: Kiểm toán cấu hình đường dẫn (`config-admin.yaml` & `admin.yaml`)
- `D:\Taadaa\Tiktok-video\config-admin.yaml`:
  - `avatar_source_root: D:\TIKTOK-videonuoinick-admin`
  - `media_source_root: D:\TIKTOK-videonuoinick-admin`
  - `video_source_root: D:\TIKTOK-videonuoinick-admin`
  - `workflow_workbook: D:\OneDrive\TaadaaData\admin\Tik1.xlsx`
- `D:\Taadaa\machine-config\admin.yaml`:
  - `host_id: admin`
  - `workbook_root: D:/OneDrive/TaadaaData/admin`

### Bước 2: Kiểm toán logic phân giải đường dẫn (`path_resolver.py`)
- Trên Admin: `D:\video goc` KHÔNG tồn tại (`exists: False`), chỉ có `D:\video goc may 2` (`exists: True`).
- Thứ tự phân giải trong `resolve_avatar_path`:
  1. `D:\video goc may 2\<folder>\avatar.jpg` (khi `video_goc` được chỉ định).
  2. Fallback sang `D:\TIKTOK-videonuoinick-admin\<folder>\avatar.jpg`.
- Bắt buộc kiểm tra 2 đầu kho Admin đồng nhất nội bộ (`video goc may 2` $\leftrightarrow$ `TIKTOK-videonuoinick-admin`).

### Bước 3: Kiểm tra công cụ trích xuất ảnh (`_make_avatar.py`)
- Nguồn video mặc định: `DEFAULT_SOURCE_ROOT = D:\video goc may 2` (tự động phát hiện khi thư mục này tồn tại).
- **Python Runtime**: BẮT BUỘC dùng `D:\CodexRuntime\tiktok-video\venv-core024\Scripts\python.exe` (đã cài sẵn `cv2 4.11.0` và `ultralytics/yolo`). Python hệ thống (`Python311`) thiếu thư viện `cv2` sẽ gây crash `ModuleNotFoundError: No module named 'cv2'`.
- Chạy thử trích xuất 1 folder có video trong `D:\video goc may 2` để bảo đảm exit code 0.

### Bước 4: Đồng bộ Sổ cái và SQLite sang Admin
- Khóa cứng `video gốc = Folder Video` trong toàn bộ `admin/Tik1..8.xlsx` (triệt tiêu 80 dòng lệch ở Tik 3).
- Đồng bộ `tiktok_tracker.db` sang `admin-farm:D:/Taadaa/data/tiktok_tracker.db`.

---

## 4. Quy trình Cứu nguy khẩn cấp nếu lỡ copy nhầm
Nếu lỡ copy file từ Kibe sang Admin:
1. Sao chép khôi phục ngay toàn bộ các avatar thật từ `D:\video goc may 2\<N>\avatar.jpg` sang `D:\TIKTOK-videonuoinick-admin\<N>\avatar.jpg`.
2. Xóa bỏ các file avatar ở những folder không có nguồn gốc trong `video goc may 2`.
3. Đối soát mã băm MD5 của Folder 1 hoặc các folder mẫu để xác nhận ảnh đúng nhân vật Admin.
