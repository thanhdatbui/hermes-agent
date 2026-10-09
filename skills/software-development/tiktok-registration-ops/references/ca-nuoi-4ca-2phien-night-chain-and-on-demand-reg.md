# Ca Nuôi (4 Ca x 2 Phiên) & Chuỗi Đêm Tuần Tự (Night Chain Sequential) & On-Demand Reg

## 1. Bản chất Ca Nuôi & Khoảng cách 2 Phiên
- **Cấu trúc 1 Ca:** Mỗi Ca phân bổ cho một Row tài khoản gồm đúng **2 Phiên**:
  - **Phiên 1 (P1):** Feed + Tương tác tự nhiên + Follow lượt 1 (~15-18 follow). Thời lượng ~45-50 phút.
  - **Khoảng nghỉ giữa 2 Phiên (Gap A):** ~45 - 75 phút. Đây là khoảng nghỉ tự nhiên của cùng 1 user trên thiết bị.
  - **Phiên 2 (P2):** Feed + Follow lượt 2 (~15-18 follow) + Đăng video (upload hook). Thời lượng ~45-50 phút.
  - **Tổng thời gian hoàn thành 1 Ca:** Tối thiểu 2h15m - 2h30m (KHÔNG THỂ hoàn thành sau 45 phút).
  - **Khoảng nghỉ giữa 2 Ca khác nhau (Gap B):** >= 3 tiếng. Đây là vùng đệm nguội máy và xoá dấu chân co-location giữa các tài khoản khác nhau trên cùng phần cứng.

## 2. Chuỗi Đêm Tuần Tự (Night Chain Sequential Pipeline)
- **Lịch kích hoạt:** Bắt đầu lúc `00:00` (Ca 4 Đêm - Row 7 ngày lẻ / Row 8 ngày chẵn).
- **Quy tắc tuyệt đối:** Các Phase nối tiếp nhau tuần tự, **Phase sau chỉ chạy khi Phase trước hoàn tất (return code)**, không dùng mốc giờ cố định:
  1. **Phase 1 (Ca 4 Feed Row 7/8):** Bắt đầu lúc 00:00 (chạy 2 phiên P1 và P2 qua `tiktok_runner` / ps1). Kết thúc lúc ~02:15 - 02:20.
  2. **Phase 2 (Reg Gmail):** Nối tiếp ngay sau khi Phase 1 return.
  3. **Phase 3 (Add 2FA TikTok):** Nối tiếp ngay sau khi Phase 2 return.
- **Loại bỏ Reg TikTok ban đêm:** Bỏ hoàn toàn bước quét dồn 80 máy reg TikTok trong đêm để tránh nghẽn mạng, nóng máy và cạn mail không cần thiết.

## 3. Cơ chế On-Demand Reg theo Ca (Just-In-Time)
- Thay vì reg dồn ban đêm, áp dụng quy tắc: **Ca nào máy nào thiếu acc ở Row của ca đó thì mới chạy reg bù trực tiếp trên máy đó.**
- **Điều kiện đếm slot hợp lệ trong Tracking Workbook (`load_registered_mailboxes`):**
  - **CẢNH BÁO NÚT THẮT:** Không được đếm tổng số dòng máy xuất hiện trong sheet, vì máy có thể có sẵn 8 dòng slot nhưng cột `ID`/`tiktok_id` rỗng (`None`).
  - **Bắt buộc:** Chỉ tăng `machine_counts[m]` khi dòng đó THỰC SỰ CÓ `tiktok_id` không rỗng (`if tiktok_id and stt_idx is not None...`). Nếu đếm cả dòng trống, hệ thống sẽ tưởng nhầm máy đã đủ 8 acc và bỏ qua vĩnh viễn!
- **Nguyên liệu Mail:**
  - Kiểm tra `gmail_clean_v2.xlsx` xem máy thiếu acc đã có mail chưa dùng hay chưa.
  - Nếu thiếu mail: Tự động gọi `buy_hotmail.py --append-kibe N --target-machines M1,M2...` để mua và nạp đúng số lượng mail cho đúng máy đó vào `D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx`.
- **Target Eligibility:** Cung cấp cờ lọc `target_stts` để `_detect_clean.py` và `social_reg_v1.py` chỉ nhắm đúng danh sách các máy đang thiếu nick ở Row cần chạy.
