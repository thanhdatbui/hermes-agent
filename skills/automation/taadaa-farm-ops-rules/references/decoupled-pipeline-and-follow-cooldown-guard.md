# Decoupled Farm Pipeline & Follow Watchdog Baseline Guard

## 1. Nguyên Tắc Độc Lập 3 Quy Trình (Feed — Follow — Upload)
- **Quy tắc tuyệt đối:** Ba quy trình vận hành chính của nick farm gồm **Lướt Feed**, **Follow chéo / Follower**, và **Đăng Video (Upload)** phải chạy hoàn toàn **độc lập**.
- **Không phụ thuộc kết quả:** Bất kể quy trình trước (ví dụ Feed) bị fail (do app crash, focus lỗi, ATX/ADB timeout hoặc mạng), quy trình tiếp theo (Follow, Upload) vẫn BẮT BUỘC được khởi động và thực thi bình thường. CẤM tự ý hủy (skip) Follow hay Upload chỉ vì Feed chưa hoàn tất.

## 2. Kỷ Luật Phạt Cờ Cooldown Nhả Follow (Anti-False-Cooldown Invariant)
- **Bản chất Optimistic UI trên TikTok:**
  - Khi tap nút Follow, TikTok app luôn lập tức chuyển nút sang trạng thái "Following / Bạn bè".
  - Nếu backend TikTok từ chối/hủy, sau 1–2 giây nhận response app mới âm thầm revert nút ngược lại thành "Follow" (nhả follow).
  - Do đó: Nếu UI hiển thị lại nút "Follow" sau khi tap thì chắc chắn là server TikTok đã từ chối lượt follow đó.
- **Chống phạt Cooldown oan (Single-Failure Cooldown Ban):**
  - CẤM TUYỆT ĐỐI áp dụng cờ phạt Cooldown 24h (`cooldown_until_date`) chỉ sau đúng 1 lần phát hiện nút bị nhả trong phiên. Một lượt bị nhả có thể do tài khoản đích bị private, giới hạn tương tác, hoặc proxy lag tạm thời, không đồng nghĩa tài khoản farm bị hạn chế tính năng.
  - Phạt Cooldown 24h chỉ được phép kích hoạt khi tài khoản dính lỗi nhả liên tiếp trên các phiên khác nhau (Streak >= 2). Lần nhả đầu tiên chỉ dừng phiên hiện tại để bảo toàn nick, không đóng băng nick sang ngày hôm sau.

## 3. Max Baseline Age Guard Trong Đối Soát TikTok Web (Watchdog)
- **Bẫy Baseline Stale 24h:**
  - Watchdog cào snapshot cuối phiên ($T_1$) và tìm snapshot trước đầu phiên ($T_0$) trong SQLite để tính delta ($T_1 - T_0$).
  - Nếu nick bị skip ở phiên trước hoặc không có snapshot đầu phiên, truy vấn `timestamp <= session_start` sẽ bị trôi ngược về snapshot từ 24h trước (hôm qua), dẫn tới việc cộng dồn toàn bộ follow của cả ngày vào phiên 30 phút, gây báo cáo lệch ảo nghiêm trọng.
- **Cơ chế Max Baseline Age Guard:**
  - Baseline snapshot bắt buộc phải nằm trong vòng **<= 4 giờ** và **cùng ngày** với thời điểm bắt đầu phiên.
  - Nếu baseline cũ hơn 4 giờ hoặc sang ngày khác: Đánh dấu rõ `baseline cũ (<timestamp>) | UNPROVEN`, tuyệt đối không tính delta trừ lùi và không tính vào sai số tổng của phiên.
