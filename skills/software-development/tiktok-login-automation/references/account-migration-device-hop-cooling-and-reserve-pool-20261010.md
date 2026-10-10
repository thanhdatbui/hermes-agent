# Quy tắc Di chuyển Tài khoản, Làm nguội Session (Device-Hop Cooling) & Quản lý Kho Dự bị (2026-10-10)

## 1. NGUY CƠ TỪ HÀNH VI DEVICE-HOP TRÊN TIKTOK
Khi một tài khoản TikTok vừa bị đăng xuất (đá ra) khỏi một thiết bị Android thật (ví dụ do gỡ nick ký sinh, trả slot cho nick chính chủ của máy):
- **Phản ứng của Server TikTok**:
  - TikTok theo dõi chặt chẽ lịch sử phiên (Session Footprint: Fingerprint phần cứng, Android ID, IMEI/Serial, MAC Wi-Fi, IP Egress).
  - Nếu vừa logout khỏi Máy A mà chỉ sau vài phút/vài giờ lập tức đăng nhập sang Máy B (khác hoàn toàn thiết bị và IP):
    1. **Bắt Verify Challenge**: Đòi mã xác minh gửi về email gốc (nếu mail gốc die hoặc chưa add 2FA TOTP là kẹt vĩnh viễn).
    2. **Flag Bot / Bất thường**: Đòi giải Captcha xoay vòng hoặc captcha trượt khó.
    3. **Shadowban / 0 View**: Thuật toán đánh tụt trust score của tài khoản mới chuyển máy nếu chưa kịp thích nghi IP mới.

---

## 2. QUY TẮC SESSION COOLING PERIOD (LÀM NGUỘI PHIÊN TỐI THIỂU 24H - 48H)
1. **Thời gian ngâm nguội bắt buộc**:
   - Tài khoản vừa đăng xuất khỏi thiết bị cũ **BẮT BUỘC NGÂM NGUỘI TỐI THIỂU 24H ĐẾN 48H** trước khi được phép nạp lên bất kỳ thiết bị mới nào.
   - Tuyệt đối CẤM đăng nhập ngay lập tức trong cùng ca làm việc hoặc cùng ngày.
2. **Nguyên tắc nạp lại lên máy mới**:
   - Khi hết thời gian ngâm 24-48h, chỉ nạp lên máy mới khi:
     * Máy mới chạy qua Proxy Singbox/MikroTik cố định ổn định (không dùng IP nhảy bất thường).
     * Máy mới còn slot trống hợp lệ (< 8 tài khoản trên Switcher).
     * Nạp xong phải chạy nuôi nhẹ (warmup lướt feed 1-2 phiên) trước khi đưa vào ca đăng video hoặc follow chéo.

---

## 3. BẢO TOÀN TÀI NGUYÊN: KHO TÀI KHOẢN DỰ BỊ (RESERVE POOL)
- **CẤM TỰ Ý XÓA/BỎ NICK LIVE**:
  - Các nick bị đá ra khỏi máy nếu là nick đã qua thời gian ngâm (tuổi reg >= 14 ngày, có followers) là **tài sản giá trị cao của Farm**.
  - Bắt buộc lưu trữ đầy đủ thông tin vào kho dự bị: `Username | Password | 2FA Secret | Email | Pass Mail | DOB | Ngày tạo | Ghi chú máy cũ`.
- **Vai trò quân dự bị**:
  - Dùng để đắp ngay vào các máy bị sự cố (ví dụ: máy bị mất nick, nick bị khóa vĩnh viễn, hoặc mail die không đổi được) mà không cần phải chờ reg nick mới và ngâm lại từ đầu.

---

## 4. KỶ LUẬT ĐỐI SOÁT SỐ MÁY KHI USER NHẮC NHẦM
- Khi User ra chỉ thị nhắc tới số máy (ví dụ: "acc thừa máy 8 nãy đá ra ấy"):
  - Coordinator **BẮT BUỘC ĐỐI SOÁT TRƯỚC** với Master Workbook (`taikhoan_dat_v2_updated .xlsx`) và lịch sử gần nhất trong session.
  - Tuyệt đối không can thiệp mù vào Máy 8 khi Máy 8 đang chạy đủ 8 nick chuẩn.
  - Phải phân biệt rõ máy vừa thao tác đá nick (ví dụ Máy 20 vừa logout nick ký sinh) để tránh gây xáo trộn nhầm máy đang vận hành ổn định.
