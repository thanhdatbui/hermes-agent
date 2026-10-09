# Profile Bio Policy for TikTok Farm (Nuôi Nick)

*Đúc kết từ tư vấn vận hành của Sol (gpt-5.6-sol) & Hermes Coordinator (18/09/2026)*

---

## 1. Bản chất thuật toán & Hành vi User thực tế
- **"No bio yet" là an toàn nhất:** Hàng trăm triệu tài khoản TikTok người thật (casual viewer, người dùng chỉ đăng clip ngắn, giải trí cá nhân) hoàn toàn không bao giờ viết bio. Đây là trạng thái mặc định phổ biến nhất trên nền tảng.
- **TikTok Trust & Safety không dùng "Bio trống" làm tín hiệu bot:**
  - Tín hiệu bot thực sự gồm: Tần suất thao tác, tốc độ lặp lại, hành vi bất thường, cụm IP trùng lặp, fingerprint thiết bị, tương tác ảo.
  - Profile có avatar thật, tên/username rõ ràng, video đăng đều đặn, view 100-400 organic là đã đủ bằng chứng "acc sống" (high trust score).
- **Phân phối video (FYP) không dùng bio:** Thuật toán đề xuất video dựa trên Retention rate, Watch time, Tương tác (Like, Share, Comment), Âm thanh (Sound) và Hashtag, hoàn toàn không phụ thuộc vào việc tài khoản có bio hay không.

---

## 2. Rủi ro khi tự động hoá nhồi Bio hàng loạt
- **Tự tạo footprint nguy hiểm:**
  - **Temporal pattern:** Cùng một thời điểm/khoảng thời gian dàn 50-100 máy vào trang Edit Profile để sửa thông tin.
  - **Linguistic footprint:** Dù dùng LLM sinh văn bản, cấu trúc ngữ pháp, độ dài câu hoặc từ ngữ đặc thù vẫn tạo cụm tương đồng.
  - **Device/IP correlation:** Hành vi can thiệp vào profile hàng loạt trên cùng một dải IP/hạ tầng farm sẽ kích hoạt bộ lọc kiểm tra bất thường.
- **Làm phức tạp hoá pipeline:**
  - Thêm bước UI Edit Profile dễ phát sinh lỗi treo UI, popup chặn, gõ phím lỗi ADB/ATX không cần thiết.

---

## 3. Khung quy định vận hành theo vòng đời acc
1. **Giai đoạn nuôi nick (Trust building - Hiện tại):**
   - **Quy tắc:** CẤM chạm vào bio. Giữ nguyên mặc định `No bio yet`.
   - **Tập trung:** Nuôi dưỡng hành vi xem video tự nhiên, đăng video đều, giữ ấm proxy/máy.
2. **Giai đoạn chuyển đổi (Monetization / Bán hàng sau này):**
   - **Điều kiện kích hoạt:** Acc đạt ngưỡng follower (ví dụ >= 1,000 follower), chuẩn bị gắn link bio, bio link affiliate hoặc làm TikTok Shop.
   - **Cách thực thi:** Sửa **thủ công từng tài khoản**, rải rác thời gian khác nhau theo ngày, văn phong hoàn toàn cá nhân hoá, tuyệt đối không chạy script hàng loạt.
