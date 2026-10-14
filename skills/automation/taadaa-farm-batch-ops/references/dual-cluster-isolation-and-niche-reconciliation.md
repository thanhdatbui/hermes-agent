# Dual-Cluster Farm Isolation & Niche Synchronization (Kibe vs Admin)

## 1. Bản Chất Kiến Trúc Dual-Cluster (2 Cụm Máy Độc Lập)
Hệ thống Farm Taadaa 8 Tik vận hành trên 2 cụm máy PC và thiết bị hoàn toàn riêng biệt:
- **Cụm Kibe (Máy 1..80, 640 acc)**:
  * Workbook: `D:\OneDrive\TaadaaData\kibe\Tik1.xlsx` .. `Tik8.xlsx`.
  * Kho video gốc: `D:\video goc\` (lưu trên PC Kibe).
  * CSDL theo dõi cào/niche: CSDL SQLite runtime tại `D:\CodexRuntime\tiktok-video\` (PC Kibe).
- **Cụm Admin (Máy 201..280, 640 acc)**:
  * Workbook: `D:\OneDrive\TaadaaData\admin\Tik1.xlsx` .. `Tik8.xlsx`.
  * Kho video gốc: `D:\video goc may 2\` (lưu trên SSD M.2 của PC Admin qua SSH).
  * CSDL theo dõi cào/niche: CSDL SQLite runtime tại `D:\CodexRuntime\tiktok-video-machine2\` (PC Admin).

## 2. Invariant Cốt Lõi: CÔ LẬP TUYỆT ĐỐI (DUAL-CLUSTER HARD ISOLATION)
- **Kênh nguồn & Video độc lập 100%**: Cùng một số thứ tự folder nguồn $F_{src}$ (ví dụ Folder 217) ở Kibe và Admin tải từ 2 kênh khác nhau, mang 2 chủ đề khác nhau, và lưu ở 2 ổ cứng khác nhau:
  * Kibe Folder 217: Kênh `@ajisai39` (figure/anime Miku) $\rightarrow$ Niche `Anime`.
  * Admin Folder 217: Kênh `@duoc.o.phanthiet` / `@ibone.vn` (ẩm thực đường phố) $\rightarrow$ Niche `Ẩm thực`.
- **CẤM TUYỆT ĐỐI ĐỒNG BỘ CHÉO**:
  * CẤM dùng CSDL của Kibe để đồng bộ Niche / Hashtag / Keyword vào thư mục `OneDrive\TaadaaData\admin\`.
  * CẤM chạy chung cron job ghi đồng thời cả 2 cụm Kibe và Admin.
  * CẤM suy diễn cùng số $F_{src}$ là dùng chung video hoặc chung niche.

## 3. Bài Học Sự Cố: "Bẫy Script Chung & Cron Tự Động Phá Dữ Liệu" (Incident 14/10/2026)
- **Nguyên nhân**: Script `sync_all_tik_keywords.py` khai báo `FARM_DIRS = [("Kibe", ...), ("Admin", ...)]` nhưng chỉ đọc CSDL Kibe. Một cron job 15 phút định kỳ tự động chạy script này và ghi đè 565/640 folder của Admin bằng nhãn Kibe!
- **Biện pháp khắc phục triệt để**:
  1. **Xóa vĩnh viễn Cron Job**: Loại bỏ hoàn toàn cron job `sync-all-tik-keywords-cron` khỏi hệ thống cron.
  2. **Cắt đứt mã nguồn**: Trong `sync_all_tik_keywords.py`, xóa bỏ hoàn toàn `Admin` khỏi `FARM_DIRS`. Script này chỉ được phép thao tác nội bộ cụm Kibe.
  3. **Tách biệt công cụ Admin**: Cụm Admin có script đồng bộ độc lập `sync_admin_real_niches.py`, đọc trực tiếp từ CSDL thật của Admin (trích xuất qua SSH từ `tiktok-video-machine2`).
  4. **Khôi phục dữ liệu**: Xuất `admin_real_folders.json` từ CSDL Admin và chạy `sync_admin_real_niches.py` để trả lại đúng 100% Niche và Hashtag Pool cho 640 folder Admin.
  5. **Preflight Validator**: Chạy `excel_preflight_validator.py` trên cả Kibe và Admin để xác nhận 0 lỗi, 0 cảnh báo.
