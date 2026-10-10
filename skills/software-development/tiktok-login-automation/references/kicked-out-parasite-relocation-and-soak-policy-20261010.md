# Chính Sách Di Chuyển & Ngâm Nguội Nick Bị Đá Ra / Ký Sinh Sau Khi Thu Hồi (Kicked-Out / Parasite Account Relocation & Soak Policy - 10/10/2026)

## 1. NGUYÊN TẮC CỐT LÕI: BẪY DEVICE HOPPING CỦA TIKTOK
- **Bối cảnh**: Khi một tài khoản TikTok (ví dụ nick già reg 26/08 như `@javialdzxxj`) bị kẹt/ký sinh nhầm trên một máy (ví dụ Máy 20) và vừa được đăng xuất an toàn qua UI Settings để trả slot cho nick chính chủ.
- **Bẫy Device Hopping**:
  - Server TikTok vừa ghi nhận event Logout trên thiết bị cũ (Samsung S7 A, IP A, Android ID A).
  - Nếu trong thời gian ngắn (< 24h - 48h) lập tức đăng nhập sang một thiết bị khác (Samsung S7 B, IP B, Android ID B), hệ thống chống gian lận của TikTok sẽ coi đây là hành vi chiếm đoạt tài khoản (Account Takeover) hoặc chuyển nhượng bất thường.
  - Hậu quả: Bắt giải Captcha trượt bất khả thi, khóa tài khoản đòi mã email khôi phục, hoặc ghim cờ Shadowban / hạn chế tương tác (0 view, cấm follow).
- **Chính sách ngâm nguội bắt buộc (Cold Soak Period)**:
  - BẮT BUỘC cho tài khoản nghỉ ngơi / ngâm nguội tối thiểu **24h - 48h** sau khi vừa logout khỏi máy cũ trước khi đăng nhập vào máy mới.
  - Khi login lên máy mới: Bắt buộc mở app qua đúng Proxy/IP gán riêng của máy đó.

## 2. QUY TRÌNH NẠP TRƯỚC VÀO SỔ SÁCH (STAGING IN WORKBOOK BEFORE LOGIN)
Trong thời gian tài khoản đang ngâm nguội (chưa login trên thiết bị), ta tiến hành xếp slot và đồng bộ trước vào Master Excel của cụm đích (ví dụ Cụm Admin Máy 255):
1. **Tìm máy và slot còn trống**:
   - Quét `taikhoan_run_safe.xlsx` hoặc `Tik1..Tik8.xlsx` của cụm (Kibe 1-80 hoặc Admin 201-280) để xác định máy có slot đang mang giá trị `None`.
   - Ví dụ: Admin Máy 255 còn trống Slot 2 (Row 2, ca Tik2, Folder Video 434, niche Yoga).
2. **Cập nhật đồng bộ cả 3 bảng**:
   - `taikhoan_run_safe.xlsx`: Điền ID tài khoản vào đúng dòng của máy và slot (ví dụ Máy 255 Slot 2 dòng 435).
   - `Tik2.xlsx`: Điền ID tài khoản vào Cột 3 (ID), giữ nguyên Folder Video và Niche đã quy hoạch (ví dụ Folder 434, niche Yoga).
   - `taikhoan_dat_v2_updated .xlsx`:
     * Chú ý cấu trúc: Sheet `Tài Khoản` của cụm Admin được xếp theo block từng ca (Tik1 từ dòng 2-81, Tik2 từ dòng 82-161...).
     * Phải chèn dòng (insert row) vào đúng vị trí ca của máy đó (ví dụ Máy 255 Slot 2 chèn tại dòng 135 ngay sau Máy 254 Slot 2 tại dòng 134).
     * Điền đầy đủ thông tin: `Máy | Folder Video | ID | PASS | 2FA | GMAIL | PASS MAIL | NGÀY THÁNG NĂM SINH | NGÀY TẠO | device ID`.
3. **Thẩm định Invariant bắt buộc trước khi commit/kết thúc**:
   - Chạy lệnh kiểm tra cấu trúc dữ liệu:
     `python D:/Taadaa/tools/excel_preflight_validator.py --excel-dir "D:/OneDrive/TaadaaData/<kibe|admin>"`
   - BẮT BUỘC đạt `PASS 100% - Toàn bộ Invariant Rules hợp lệ (0 cảnh báo)`.

---

## 3. BẢO TOÀN ĐỘC LẬP KHO VIDEO (VIDEO FOLDER ISOLATION) VÀ TIẾP NỐI TIẾN ĐỘ
Khi xử lý cặp tài khoản "Nick cũ được cứu" và "Nick ký sinh bị đá ra":
1. **Cô lập kho video 100% giữa 2 tài khoản**:
   - Khi nick ký sinh bị gán nhầm, nó thường trỏ chung vào Folder Video của nick cũ (ví dụ Folder 153 của Kibe).
   - Khi chuyển nick ký sinh sang máy/cụm khác (ví dụ Admin M255 Slot 2), **BẮT BUỘC cấp Folder Video mới hoàn toàn theo quy hoạch của máy/cụm mới** (ví dụ Folder 434 thuộc kho Admin `D:\TIKTOK-videonuoinick-admin\434` trên `admin-farm`).
   - Tuyệt đối không để 2 nick trỏ cùng 1 Folder Video dù ở khác máy hay khác cụm (tránh bẫy duplicate content của TikTok).
2. **Quy tắc tiếp nối tiến độ đăng video**:
   - **Nick ký sinh chuyển sang vị trí mới**: Reset `Video Đã Đăng` về `0` trong `Tik*.xlsx` và `taikhoan_run_safe.xlsx` để bot bắt đầu đăng từ clip `1.mp4`.
   - **Nick cũ vừa được phục hồi**: **BẮT BUỘC giữ nguyên số video đã đăng trong lịch sử** (ví dụ đã đăng 21 video thì ghi nhận đúng 21). Ca đăng tiếp theo sẽ lấy clip kế tiếp (ví dụ `22.mp4`). **CẤM reset về 0** khiến bot đăng lặp lại các clip cũ.

---

## 4. ĐỐI SOÁT XÁC THỰC KÊNH GỐC VÀ TĂNG TRƯỞNG TỰ NHIÊN (ORGANIC METRICS AUDIT)
Trước khi đưa nick cũ vừa phục hồi trở lại lịch chạy tự động:
1. **Đối soát 3 lớp với cơ sở dữ liệu (`tiktok_tracker.db`)**:
   - Tra cứu bảng `snapshots` theo `username`:
     * UID tài khoản khớp chính xác UID lịch sử.
     * Ngày tạo / ngày sinh khớp với hồ sơ gốc (ví dụ reg 04/03/2026).
     * Số lượng video hiển thị trên profile khớp số lượng video đã đăng.
2. **Đánh giá sức khỏe qua chỉ số tăng trưởng tự nhiên (Organic Metrics)**:
   - Trong thời gian kênh tạm dừng đăng, đối soát chuỗi `snapshots` theo thời gian:
     * Nếu Follower và Like (Heart) vẫn nhích tăng đều (ví dụ +5 fl, +17 likes trong thời gian nghỉ), đây là bằng chứng thép chứng minh:
       - Thuật toán TikTok vẫn đang phân phối video cũ.
       - Kênh hoàn toàn khỏe mạnh, không bị shadowban, gậy vi phạm hay bóp tương tác.
     * Khi resume đăng clip tiếp theo, kênh sẽ bắt nhịp đề xuất lại rất nhanh.
