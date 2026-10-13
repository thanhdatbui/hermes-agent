# Lỗ Hổng Từ Điển Audit (Audit Dictionary Blindspot) & Cơ Chế Lọt Niche Cũ Trên Farm

## 1. Hiện Tượng (User Frustration)
- Người dùng đặt câu hỏi: *"Chuẩn hoá hashtag rồi sao cứ lâu lâu lại lòi ra acc sai?"*
- Kênh thực tế là **Bé Mina / Chăm sóc bé / Gia đình** (video bé chạy ở biển, gặp bà nội, đi siêu thị, nhạc thiếu nhi), nhưng trong `Tik2.xlsx` dòng Máy 33 (@thy.dung4581) và bảng `Hashtag theo Folder` vẫn bị gán nhầm **`Keyword: Gym`** và hashtag `#gym #tapgym #tapluyen`.

## 2. Nguyên Nhân Kỹ Thuật Gốc Rễ (Root Cause)
1. **Thiếu Phủ Kín Niche trong Tool Audit (`audit_video_niche_mismatches.py`)**:
   - Bộ từ khóa `NICHE_KEYWORDS` của tool audit trước đây chỉ cấu hình 10 nhóm chủ đề: `thucung`, `oto`, `xemay`, `amthuc`, `haihuoc`, `cauchuyen`, `gym`, `yoga`, `lamdep`, `game`.
   - **HOÀN TOÀN THIẾU các niche `chamsocbe`, `giadinh`, `mevabe`, `embe`, `thieunhi`**.
2. **Cạm bẫy "Default-Pass" (Audit False-Negative)**:
   - Khi audio trích xuất từ video folder 113 có lời bài hát thiếu nhi rõ ràng (*"mi cong cong cong mắt tròn xoe nhìn ai cũng thấy say mê nụ cười má hồng..."*), tool đối chiếu từ khóa nhưng không khớp với bất kỳ niche nào trong 10 nhóm có sẵn.
   - Kết quả: `detected_niche = null`.
   - Thuật toán audit kiểm tra: `if detected_niche is not None and detected_niche != current_niche: mismatch = True else: mismatch = False`.
   - Vì `detected_niche` là `null`, tool **mặc định coi `mismatch = False`** (bỏ qua, coi là hợp lệ). Kết quả được ghi vào `niche_audit_results.json`:
     ```json
     {"folder": 113, "current_niche": "gym", "detected_niche": null, "mismatch": false}
     ```
3. **Cơ Chế Re-sync Tự Động Duy Trì Nhãn Sai**:
   - Script `sync_all_tik_keywords.py` lấy sheet `Hashtag theo Folder` và database quản lý trạng thái làm Single Source of Truth (SoT).
   - Vì đợt audit trước bỏ sót folder 113, nhãn `Gym` vẫn tồn tại trong SoT.
   - Mỗi chu kỳ sync tự động, script trung thành đồng bộ lại `#gym #tapgym` vào `Tik2.xlsx`, tạo ra ảo giác "chuẩn hóa rồi mà lâu lâu lại lòi ra acc sai".

## 3. Quy Tắc Khắc Phục & Ngăn Chặn Bắt Buộc (Invariants)
1. **Cấm Tuyệt Đối "Default-Pass" Khi `detected_niche = null`**:
   - Khi `detected_niche is None` nhưng folder đang mang một niche đặc thù (như `gym`, `yoga`, `game`, `oto`), tool audit KHÔNG ĐƯỢC tự động kết luận `mismatch = False`.
   - Phải gắn trạng thái `AUDIT_COVERAGE_GAP` hoặc `UNCLASSIFIED` để cảnh báo operator bổ sung dictionary hoặc review thủ công.
2. **Bổ Sung Đầy Đủ Dictionary Cho Các Niche Trẻ Em & Gia Đình**:
   - Luôn đảm bảo `NICHE_KEYWORDS` trong `audit_video_niche_mismatches.py` có tối thiểu:
     ```python
     'chamsocbe': ['bé', 'em bé', 'trẻ em', 'thiếu nhi', 'mẹ và bé', 'chăm sóc bé', 'bỉm sữa', 'nuôi con', 'mầm non', 'mẹ bầu'],
     'giadinh': ['gia đình', 'bố mẹ', 'ông bà', 'vợ chồng', 'con cái', 'nhà mình', 'sum họp'],
     ```
3. **Quy Trình Sửa Dứt Điểm Khi Phát Hiện Lệch Niche**:
   - Bước 1: Cập nhật trực tiếp sheet `Hashtag theo Folder` trong `Tik<Slot>.xlsx` tại dòng folder $F_{src}$ ($F_{src} = (Slot - 1) \times 80 + M$).
   - Bước 2: Cập nhật sheet `TaiKhoan` cột `Keyword Video` và `Hashtag Pool`.
   - Bước 3: Đưa folder vào `manual_avatar_protected_folders.json` để khóa bảo vệ SSOT.
   - Bước 4: Chạy `sync_all_tik_keywords.py` để đồng bộ nhất quán trên toàn bộ cluster Kibe & Admin.
