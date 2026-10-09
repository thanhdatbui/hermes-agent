# External / Priority Target Architecture: Đưa Nick Ngoài Farm Vào Danh Sách Follow / Feed

## 1. Bản chất kiến trúc: Phân định Actor (Tài khoản thực thi) vs Target (Tài khoản mục tiêu)
- **Actor (Nick farm / Tài sản):** Là các tài khoản có session đăng nhập, cookie, token trên máy Samsung S7 (quản lý qua `taikhoan_dat_v2.xlsx`, `tik1.xlsx` -> `tik8.xlsx`, `tiktok_tracker.db`). Giới hạn cứng TikTok app là tối đa 8 tài khoản/thiết bị (`MAX_TRACKING_ACCOUNTS_PER_MACHINE = 8`).
  - *Pitfall cấm kỵ:* Tuyệt đối KHÔNG đưa nick ngoài farm vào workbook kho nick hoặc tạo Row 9 giả định trong Excel. Máy sẽ cố switch/login -> fail OTP/checkpoint -> kẹt máy và văng lỗi recovery.
- **Target (Mục tiêu tương tác):** Là đối tượng nhận follow, view, like từ máy farm. Nick ngoài farm (như nick cá nhân của user) chỉ được phép tồn tại ở tầng Target.

## 2. Rủi ro thuật toán khi follow nick cá nhân từ dàn farm
- **Algorithmic Poisoning (Hỏng tệp người xem):** Nick farm lướt tạp/chưa có ngách cụ thể. Nếu dồn dập tương tác vào nick cá nhân, TikTok hiểu nhầm tệp khán giả -> khi ra video mới sẽ phân phối cho nick clone/rác -> tụt reach tự nhiên.
- **Shadow-drop (TikTok nhả follow ngầm):** Nếu máy farm độ trust thấp (đang dưỡng sinh, mới reg) đi follow, sau 24h-48h TikTok sẽ tự động trừ follow ảo (silent drop).
- **Bot Network Flag:** Cùng IP/cùng cluster máy tìm kiếm và follow ồ ạt trong thời gian ngắn -> kênh mục tiêu bị ăn cờ gian lận / shadowban.

## 3. Cơ chế giải quyết tối ưu: Priority Target Queue + Drip-feed Capping
Thay vì random sampling hên xui (dễ trúng nick farm yếu hoặc tỷ lệ quá loãng):
1. **Priority Queue:**
   - Khai báo nick ngoài trong danh sách ưu tiên (`priority_targets`).
   - Runner kiểm tra `follow_state.db`: nếu máy hiện tại chưa từng follow target này, đẩy target lên vị trí ưu tiên đầu danh sách session (Top 1).
2. **Organic Flow Bắt Buộc (Search -> Watch -> Like -> Follow):**
   - Không follow trực tiếp từ URL/deep-link.
   - Thao tác: Lướt feed tự nhiên -> Search UID -> Mở profile -> Xem tối thiểu 1-2 video (giữ watch time > 60%) -> Like -> Mới bấm Follow.
3. **Drip-feed Cap (Giới hạn cứng an toàn):**
   - Khóa quota: Tối đa 5 - 10 follow/ngày cho nick ngoài.
   - Khi đủ quota ngày, các máy tiếp theo tự động bypass target này để tránh dồn dập.
   - Chọn lọc máy có trust score cao (các máy chạy Row 1/2 - Tik1/Tik2 lâu năm) ghé thăm để đảm bảo không bị silent drop.
