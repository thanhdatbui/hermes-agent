# Kiến Trúc 2 Cụm Máy Farm (Dual-Cluster) & Kỷ Luật Gộp Dữ Liệu Toàn Farm

## 1. Cấu trúc 2 Cụm Máy Farm (Kibe vs Admin)
Farm Taadaa được chia làm 2 cụm máy độc lập, lưu trữ dữ liệu tại 2 thư mục riêng biệt trên OneDrive:
- **Cụm Kibe (Farm Kibe)**:
  - Dải máy: `Máy 1` đến `Máy 80`.
  - Thư mục dữ liệu: `D:/OneDrive/TaadaaData/kibe/`
  - Các file trọng yếu: `taikhoan_run_safe.xlsx`, `taikhoan_dat_v2_updated .xlsx`, `Tik1.xlsx` .. `Tik8.xlsx`, `gmail_clean_v2.xlsx`.
- **Cụm Admin (Farm Admin)**:
  - Dải máy: `Máy 201` đến `Máy 280`.
  - Thư mục dữ liệu: `D:/OneDrive/TaadaaData/admin/`
  - Các file trọng yếu: `taikhoan_run_safe.xlsx`, `taikhoan_dat_v2_updated .xlsx`, `Tik1.xlsx` .. `Tik8.xlsx`, `gmail_clean_v2.xlsx`.

## 2. Kỷ Luật Data Aggregation (Toàn Farm)
Mọi script/tool hoặc tác vụ thống kê, báo cáo, giám sát toàn farm (TikTok Account Tracker, Daily Checklive, Stock Check, Inventory Report, v.v.):
1. **BẮT BUỘC gộp cả 2 cụm**:
   - Khi tham số nguồn (`--source`, `excel_path`) để mặc định hoặc khi báo cáo với danh nghĩa "Toàn Farm / Farm Alert", script PHẢI tự động nạp đồng thời cả 2 file:
     - `D:/OneDrive/TaadaaData/kibe/<file>.xlsx`
     - `D:/OneDrive/TaadaaData/admin/<file>.xlsx`
2. **CẤM Hardcode 1 cụm**:
   - Nghiêm cấm việc chỉ check file tồn tại đầu tiên rồi break (dẫn đến việc chỉ quét cụm Kibe máy 1-80 và bỏ sót toàn bộ cụm Admin máy 201-280).
3. **Deduplication & Mapping**:
   - Dải số máy là phân biệt tuyệt đối: Kibe (1..80), Admin (201..280).
   - Khi gộp, deduplicate username/account_id bằng cách chuẩn hóa (`str(account_id).strip().lstrip('@')`).
   - Tổng số nick toàn farm thực tế = Số nick hợp lệ Kibe + Số nick hợp lệ Admin.
