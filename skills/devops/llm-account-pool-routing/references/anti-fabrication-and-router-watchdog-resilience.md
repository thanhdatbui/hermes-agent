# Kỷ Luật Tuyệt Đối: Chống Gian Lận Kết Quả Kiểm Chứng (Anti-Fabrication Invariant)

## 1. Nguyên Tắc Cốt Lõi (Inviolable Invariant)
1. **Failure Is A Valid Outcome**: Thất bại, timeout, connection reset, lỗi cú pháp là kết quả hoàn toàn hợp lệ và BẮT BUỘC phải báo cáo trung thực 100% cho User ngay lập tức.
2. **CẤM TUYỆT ĐỐI Báo Cáo Láo / Lấy Log Cũ Thay Thế**: Tuyệt đối không được phép đọc SQLite/File log cũ trong quá khứ để lấy kết quả review/test của vài tiếng trước hay phiên trước rồi mạo danh là "vừa chạy xong".
3. **Freshness Verification Bound**: Mọi kết quả gọi external model (Sol, Claude, Codex...) chỉ được công nhận khi có request thật phát sinh trong chính turn hội thoại hiện tại (hoặc trong vòng <= 5 phút).
4. **Footnote Xác Thực Gọn Nhẹ (Tránh Spam)**:
   - Thay vì nã cả block log cồng kềnh lên Telegram, chỉ cần đính kèm 1 dòng footnote kín đáo ở cuối câu trả lời:
     `[Verified: Sol High • 26.7s • Log: <request_id> • Freshness: Live]`
   - Nếu call thất bại: Báo thẳng lỗi kỹ thuật và hỏi ý kiến User, cấm tự ý tìm cách "chữa cháy" bằng dữ liệu giả.

---

## 2. Giải Phẫu Bệnh Học Router & Watchdog (Sự Cố 22/09)

### Bệnh 1: Bão 429 + Watchdog Ngộ Sát (The 5s Kill Loop)
- **Cơ chế**: Worker gọi vào acc cạn quota liên tục mỗi 30s. Request context khủng (160k-220k tokens) làm Event Loop Node.js bị trễ.
- **Hậu quả**: Endpoint `/api/health` phản hồi mất 5.9s. Watchdog cấu hình `-TimeoutSec 5` hiểu nhầm là server chết nên SIGKILL tiến trình, gây vòng lặp restart vô tận (`Server is unreachable. Reconnecting...`). Mọi kết nối in-flight (kể cả Sol) đều bị rớt socket.
- **Khắc phục**:
  - Nâng timeout health check trong `omniroute_watchdog.ps1` lên 15s (`-TimeoutSec 15`).
  - Phải restart lại tiến trình PowerShell của watchdog để nạp tham số mới.

### Bệnh 2: Bẫy Cột Resilience Dashboard (API Key vs OAuth)
- **Hiện tượng**: User/Agent vào Dashboard chỉnh `Use upstream 429 hints = Always on` ở cột "API KEY PROVIDERS" nhưng tài khoản Antigravity upstream thực chất là loại **OAuth** (`auth_type: oauth`).
- **Khắc phục**: Phải bật cho **CẢ 2 CỘT (OAuth Providers lẫn API Key Providers)** với `maxBackoffSteps = 8-9`. Khi dính `quota_exhausted`, acc sẽ bị cách ly 1 tiếng, không bị nã lại làm sập server.

### Bệnh 3: Priority Gap Starvation trong Cache-Optimized
- **Cơ chế**: Khi các acc Pro khác cạn quota, acc nào có priority số nhỏ hơn (ví dụ 13) sẽ bị băm Rendezvous Hash dồn 100% request vào nó, khiến acc đó kiệt sức trong khi các acc priority 14, 36, 113 ngồi chơi.
- **Khắc phục**: Phải kéo priority của toàn bộ acc Pro còn quota khả dụng về sát nhau (13-14) để chia đều tải song song, đồng thời giữ nguyên `stickyRoundRobinLimit: 8` để bảo toàn prompt cache.
