# Background Process Anti-Hijack & Phân Biệt Rạch Ròi Slot-Fill vs Session-Lost (2026-09-22)

## 1. Bối cảnh & Hiện tượng (User Correction 22/09/2026)

### Sự cố 1: Background Notification Hijack Hội thoại
- Khi một background process (e.g. `proc_7947e873b06b` chạy `tiktok_login_v1.py` cho máy 32 hay máy 1) từ tác vụ cũ kết thúc, Hermes runtime tự động bơm thông báo:
  `[IMPORTANT: Background process proc_... completed normally]` kèm log tail lỗi login OTP vào giữa cuộc hội thoại.
- Ngay sau đó, User gửi một tin nhắn ngắn: `?`.
- **LỖI CỦA COORDINATOR:** Tự động giả định dấu `?` của User là yêu cầu phân tích lỗi login của Máy 1, nhảy bổ vào mở log Gmail, inspect lỗi OTP và viết báo cáo dài về `tranngan767`.
- **PHẢN ỨNG CỦA USER:** *"Session này t nhắc gì đến log in tiktok à?"* và dẫn chứng User thực ra đang hỏi về câu hỏi dang dở của Coordinator trước đó: *"[Replying to: "Có vài máy onl thêm, cài bản ms nhất luôn k?"] ?"*.

### Sự cố 2: Gây Hoang Mang Về Rủi Ro Văng Nick (False Account-Lost Alarm)
- Khi Coordinator báo cáo về Máy 1: *"Tài khoản Gmail tranngan03012004@gmail.com CHƯA ĐƯỢC ĐĂNG NHẬP VÀO MÁY 1... login fail"*.
- Do thiếu ngữ cảnh phân định, User ngay lập tức lo sợ việc nâng cấp TikTok 47.0.3 đã xóa sổ tài khoản trên máy: *"Còn máy 1 bị văng account hay gì thế?"*.
- Thực tế: Máy 1 vẫn còn nguyên vẹn 2 tài khoản (`duongkien1202`, `ginnyhanstei80`), lệnh login thất bại kia chỉ là script background đang cố nạp thêm nick thứ 3 vào slot trống của Excel.

---

## 2. Quy tắc Bắt Buộc: Anti-Hijack khi có Background Process Notification

1. **Background Notification Là Output Thụ Động (Passive Context):**
   - Thông báo `[IMPORTANT: Background process ...]` không phải là chỉ thị mới từ User.
   - Tuyệt đối CẤM đổi trọng tâm phiên làm việc hoặc chuyển sang debug lỗi của background job trừ khi User đích danh yêu cầu.

2. **Quy tắc Giải Mã Tin Nhắn Ngắn (`?`, `sao thế`, `sao v`):**
   - Khi User gửi tin nhắn ngắn ngay sau một background notification:
     - Bước 1: Kiểm tra xem turn trước Coordinator có đang hỏi User câu gì chưa được trả lời không.
     - Bước 2: Kiểm tra User có quote / reply tin nhắn nào không (`[Replied-to ...]` hoặc `[Replying to: ...]`).
     - Bước 3: Nếu User không nhắc đến tên script hay lỗi trong background notification, TUYỆT ĐỐI KHÔNG giải thích lỗi background. Hãy trả lời câu hỏi còn dang dở của session chính.

3. **Kỷ luật Phân Biệt Rạch Ròi: Slot-Fill (Nạp mới) vs Session-Lost (Văng nick cũ):**
   - Bất cứ khi nào nhắc đến lỗi đăng nhập / login trên farm, BẮT BUỘC phải mở đầu bằng định danh trạng thái:
     - **[SLOT-FILL / NẠP NICK MỚI]:** *"Nick cũ trên máy vẫn 100% nguyên vẹn. Script đang cố nạp thêm nick mới vào slot trống của Excel nhưng thiếu OTP."*
     - **[SESSION-LOST / VĂNG NICK]:** *"Nick đang chạy bị đăng xuất/văng ra ngoài."*
   - CẤM TUYỆT ĐỐI dùng từ ngữ mập mờ *"login fail"*, *"không đăng nhập được"* mà không khẳng định tình trạng các nick hiện hữu trên máy, tránh gây hoảng loạn về an toàn tài sản farm.
