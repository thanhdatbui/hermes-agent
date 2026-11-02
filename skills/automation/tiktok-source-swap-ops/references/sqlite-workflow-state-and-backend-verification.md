# Bổ sung Bảng `tiktok_workflow_state` trong SQLite SSOT và Cơ chế Tách Biệt Kiểm Chứng

## 1. Bảng `tiktok_workflow_state` trong `D:/Taadaa/data/farm_master.db`
- Thay thế hoàn toàn 8 file workbook `Tik1.xlsx` .. `Tik8.xlsx` để triệt tiêu lỗi file lock OneDrive.
- Schema bảng:
  - `machine_id` (INTEGER): ID máy (1-80 Kibe, 201-280 Admin).
  - `slot_no` (INTEGER): Slot tài khoản (1-8). PK kép `(machine_id, slot_no)`.
  - `device_serial` (TEXT): Serial thiết bị ADB.
  - `username` (TEXT): TikTok username.
  - `folder_render` (TEXT): Thư mục video đã render (`D:/video render/...`).
  - `folder_raw` (TEXT): Thư mục video gốc (`D:/video goc/...`).
  - `niche_keyword` (TEXT): Từ khóa ngách (vd: "Câu chuyện", "Gái xinh").
  - `hashtag_pool` (TEXT): Danh sách hashtag phân cách bằng dấu cách.
  - `posted_count` (INTEGER): Con trỏ video đã đăng (offset render).
  - `avatar_status` (TEXT): Trạng thái avatar (`OK`, `REPLACE_PENDING`).
  - `updated_at` (TEXT): ISO timestamp cập nhật lần cuối.
- Thư viện truy xuất Data Access Layer: `D:/Taadaa/tools/farm_sqlite_dal.py` (WAL mode, busy_timeout 15s).

## 2. Kỷ luật kiểm chứng (Anti-Canary Fallacy):
- Khi cập nhật cấu trúc database, migration dữ liệu hay viết DAL:
  - **CẤM TUYỆT ĐỐI** kích hoạt bước Canary trên điện thoại thật (`canary_runner.py`) để chụp ảnh splash app TikTok đối phó.
  - Bằng chứng nghiệm thu duy nhất: **Focused Test < 30s** kết hợp **Read-Back SQLite / DAL**.
  - Pipeline sửa code phải sử dụng cờ `--no-canary --no-canary-reason "Backend DAL SQLite"`.
