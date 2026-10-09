# Case UI-70: Phân Tách Sổ Cái Vận Hành & View Danh Bạ Gộp Đọc (Separated Source vs Unified View)

## 1. Bối cảnh & Vấn đề kiến trúc Farm 160 máy
Khi mở rộng hệ thống TikTok Automation từ cụm Kibe (Máy 1–80) sang cụm Admin (Máy 201–280), phát sinh nhu cầu:
- Các nick trên toàn farm có thể follow chéo lẫn nhau để mở rộng đồ thị graph, tránh cô lập vòng tròn.
- **Cám dỗ sai lầm:** Gộp tất cả các file Excel (`taikhoan_dat_v2_updated .xlsx`, `Tik1.xlsx`..`Tik8.xlsx`, `taikhoan_run_safe.xlsx`) thành 1 file duy nhất cho cả 160 máy.

## 2. Phán quyết kiến trúc (Sol Lead Architect & Security Auditor)
> **"KHÔNG GỘP HẾT EXCEL VÀO MỘT FILE. Gộp logic để đọc — tuyệt đối KHÔNG gộp vật lý để vận hành."**

### Tại sao CẤM GỘP file vận hành (Tầng 1)?
1. **Thảm họa File Lock & OneDrive Sync Conflict:** Nhiều runner cùng đọc/ghi trạng thái upload/nuôi đồng thời vào 1 file Excel trên OneDrive sẽ sinh hàng loạt bản sao xung đột (`...-DESKTOP-xxx.xlsx`), hỏng file (corrupted) và mất dữ liệu.
2. **Single Point of Failure (SPOF):** 1 file Excel bị khóa hoặc corrupt sẽ làm tê liệt toàn bộ 160 máy đồng loạt (cả 2 cụm). Để riêng giúp cô lập sự cố (blast radius cô lập trong 1 cụm).
3. **Bán kính rò rỉ (Blast Radius):** Sổ cái chứa credentials (email, pass, 2FA). Gộp chung phá vỡ phân quyền và cô lập bảo mật.

## 3. Giải pháp chuẩn kiến trúc: Separated Source, Unified View

### A. Tầng dữ liệu vận hành: Tách biệt tuyệt đối
- Cụm Kibe: `D:/OneDrive/TaadaaData/kibe/` (`taikhoan_dat_v2_updated .xlsx`, `Tik1`..`Tik8`, `taikhoan_run_safe.xlsx`).
- Cụm Admin: `D:/OneDrive/TaadaaData/admin/` (`taikhoan_dat_v2_updated .xlsx`, `Tik1`..`Tik8`, `taikhoan_run_safe.xlsx`).

### B. Tầng dữ liệu đích Follow: View gộp Read-Only
- Xuất file gộp: `D:/OneDrive/TaadaaData/taikhoan_run_safe_combined.xlsx` qua script `sync_combined_safe_workbook.py`.
- Ghép cột `May`, `Device ID`, `ID`, `Video Đã Đăng` từ 2 file safe (611 Kibe + 319 Admin = 930 UIDs).
- File này thuần túy là **Read-Only**: Runner follow chỉ đọc danh sách UID, tuyệt đối không ghi đè vào file.
- Ghi đè file bằng cơ chế nguyên tử (atomic write via temp file trên cùng ổ đĩa `D:`).
- Móc hook tự động: `hermes_taikhoan_sync_cron.py` tự động kích hoạt sync file gộp sau mỗi lần sync tài khoản.

## 4. Hard Gate Anchor Mode 2 (`follow_engine.py`)
- **Quy tắc bắt buộc:** Anchor của Mode 2 (để search bung danh sách following mồi) **BẮT BUỘC chỉ lấy từ dàn Kibe (`machine <= 80` và $\ge 10$ video)**.
- **Loại trừ dàn Admin:** Nick máy 201–280 dù ở hàng Tik1/Tik2 cũng không bao giờ bị bốc làm Anchor vì graph following chưa dày. Nick Admin chỉ nằm trong pool làm đích được follow (target pool).
- Kiểm tra xác minh: `FollowEngine.anchor_uids()` phải lọc `uid_to_machine.get(uid, 999) <= 80`.

## 5. Hiện tượng thống kê số liệu Dashboard vs Runner (Case Note thực tế)
1. **Tại sao Dashboard cào hiện 1004 nick mà Runner chỉ có 930 UIDs?**
   - Dashboard cào đếm tổng số dòng (rows) raw trong 2 cuốn sổ cái gốc `taikhoan_dat_v2_updated .xlsx`:
     - Sổ cái Kibe: 640 dòng (80 máy x 8 slot).
     - Sổ cái Admin: 364 dòng.
     - Tổng cộng raw rows: 640 + 364 = **1004 dòng**.
   - Runner follow đọc `taikhoan_run_safe_combined.xlsx` đã lọc trùng UID: 611 Kibe + 319 Admin (do bên Admin có 45 nick duplicate gán nhiều hàng) = **930 Unique UIDs**.
2. **Tại sao 80 máy Kibe x 2 slot (Tik1 + Tik2) = 160 nick mà Anchor chỉ có 122?**
   - Điều kiện Anchor Mode 2 là: `Tik1/Tik2` VÀ `video_count >= 10`.
   - Trong 160 slot Tik1/Tik2 của Kibe: 123 nick đủ $\ge 10$ video (trừ 1 nick đang active = 122), có **37 nick chưa đủ 10 video** nên bị loại an toàn khỏi pool Anchor. Khi nuôi đủ 10 video sẽ tự động được đưa vào Anchor.
