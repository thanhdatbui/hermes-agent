# Kỷ luật Chuẩn hóa Ngưỡng Watchdog Upload & Sửa Script Thay vì Ghi Memory

## 1. Bản chất Sự cố & Bẫy Phản xạ Ngớ ngẩn
Khi người dùng phản ánh: *"Các nick mới bị chậm 1 ca thì không cần báo trong report đâu"*:
- **Sai lầm chết người:** Agent tự ý gọi `memory(action='replace')` hoặc `memory(action='add')` lưu ghi chú vào memory cá nhân như một phản xạ đối phó.
- **Hậu quả:**
  1. Cronjob và Watchdog (ví dụ: `daily-stale-upload-accounts-watchdog`, chạy script `cron_stale_upload_watchdog.py` $\rightarrow$ `audit_stale_upload_accounts.py`) chạy hoàn toàn tự động và độc lập trong tiến trình Python nền của hệ điều hành.
  2. Chúng **hoàn toàn không bao giờ đọc conversation memory của LLM**.
  3. Báo cáo hàng ngày trên Telegram vẫn sẽ tiếp tục in nguyên vẹn danh sách cảnh báo ảo, gây ức chế cho người vận hành.
- **Quy tắc bất biến:** Mọi yêu cầu thay đổi tiêu chuẩn báo cáo, ngưỡng cảnh báo, hoặc bộ lọc tài khoản **BẮT BUỘC PHẢI THI CÔNG TRỰC TIẾP VÀO SCRIPT/CODEBASE**.

---

## 2. Toán học Chu kỳ Farm (4 Ngày / 96h) & Ngưỡng Cảnh báo Trễ

### Chu kỳ vận hành thực tế
Farm Taadaa hoạt động theo chu kỳ cố định 4 ngày (96h):
- **Day 0:** Ca 1 (Row 1) – Ca 2 (Row 3) – Ca 3 (Row 5)
- **Day 1:** Ca 1 (Row 2) – Ca 2 (Row 4) – Ca 3 (Row 6)
- **Day 2:** Ca 1 (Row 7) – Ca 2 (Row 8) – Ca 3 (Dưỡng sinh)
- **Day 3:** Dưỡng sinh xả tải toàn farm

Mỗi slot tài khoản (Tik 1 đến Tik 8) chỉ được nuôi và upload **đúng 1 lần sau mỗi 96 giờ (4 ngày)**.

### Phân tích độ trễ (Latency Analysis)
1. **Hoạt động bình thường (Normal Cadence):**
   - Khoảng cách giữa 2 lần đăng video liên tiếp là **4 ngày**.
2. **Chậm đúng 1 ca (Missed 1 Shift):**
   - Nếu nick vì lý do khách quan (lag UI, editor chậm mở caption, rớt focus màn hình chờ, hoặc hoãn ca) mà không đăng được ở ca của nó:
   - Nick đó phải đợi đến ca tiếp theo sau 4 ngày nữa.
   - Tổng số ngày không có video mới: $4 + 4 = 8$ ngày (hoặc đến 9 ngày nếu vướng ngày dưỡng sinh).
   - **Đây là dao động vận hành tự nhiên**, nick hoàn toàn khỏe mạnh, không hề bị đóng băng và sẽ tự động đăng bù ở ca kế tiếp.
3. **Chậm từ 2 ca trở lên (Missed $\ge 2$ Shifts):**
   - Khoảng cách không có video mới: $4 \times 3 = 12$ ngày (hoặc $> 9$ ngày).
   - Đây mới là thời điểm cần phát tín hiệu **Cảnh báo trễ (Warning Stale)**.
4. **Nguy cơ đóng băng (Critical Stale):**
   - Khoảng cách $\ge 14$ ngày (tương ứng bỏ lỡ từ 3–4 ca liên tiếp).

### Sai lầm của ngưỡng cũ (`days_threshold = 7`)
- Trước đây, `audit_stale_upload_accounts.py` đặt mặc định `days_threshold = 7`.
- Vì 7 ngày $< 8$ ngày, nên **toàn bộ các nick mới chỉ chậm đúng 1 ca** đều bị xếp nhầm vào danh mục `Cảnh báo trễ (7 - 14 ngày)`, sinh ra hơn 100 cảnh báo rác mỗi sáng.
- **Chuẩn hóa bắt buộc:** Nâng `days_threshold` lên **9 ngày** (hoặc 10 ngày).
  - $\le 9$ ngày: Đang đăng đều / Hoạt động bình thường (bao gồm cả dung sai chậm 1 ca).
  - $10 – 14$ ngày: Cảnh báo trễ ($\ge 2$ ca bị bỏ lỡ).
  - $> 14$ ngày: Nguy cơ đóng băng ($\ge 3$ ca bị bỏ lỡ).
