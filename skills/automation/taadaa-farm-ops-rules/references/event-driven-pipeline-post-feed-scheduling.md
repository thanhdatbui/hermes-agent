# Event-Driven Post-Feed Pipeline Scheduling (Reg Gmail & Add 2FA)

## 1. Bối cảnh & Vấn đề với Lịch Cron Giờ Cố Định (Fixed-Hour Pitfall)
- **Xung đột tài nguyên vật lý**: Đặt giờ cố định (ví dụ 01:00 AM cho `night-chain-reg-pipeline` hoặc 15:00 cho 2FA Gmail) dẫn đến nguy cơ đè máy nghiêm trọng khi các ca nuôi feed bị lệch nhịp hoặc chạy trễ (ví dụ Ca 4 lúc 01:30 đè lên chuỗi reg đêm 01:00).
- **Lãng phí thời gian rảnh**: Khi ca nuôi kết thúc sớm, hệ thống phải ngồi chờ hàng tiếng tới giờ cố định mới bắt đầu chạy các tác vụ phụ trợ.

## 2. Quy tắc Điều Phối Cuốn Chiếu Sau Ca (User Rule 2026-09-13)

### A. Tách bạch và phân bổ theo ca:
1. **Sau Ca Sáng (Ca 1 Phiên 2 hoàn tất, khung 08:30 - 11:30)**:
   - Kích hoạt Watchdog Bật 2FA Google Authenticator cho các tài khoản Gmail ngâm đủ $\ge 24\text{h} - 48\text{h}$.
   - Tận dụng khoảng trống trước khi Ca 2 bắt đầu lúc 12:00.
2. **Sau Ca Trưa (Ca 2 Phiên 2 hoàn tất, khung 14:30 - 17:30)**:
   - Kích hoạt Watchdog Chuỗi Trưa:
     $$\text{Ca Trưa Xong} \longrightarrow \textbf{Phase 1: Reg Gmail} \longrightarrow \textbf{Phase 2: Add 2FA TikTok} \longrightarrow \text{Báo cáo}$$
   - Tận dụng khoảng trống lớn 3 tiếng rảnh rỗi trước khi Ca 3 bắt đầu lúc 18:00.
3. **Bỏ Reg TikTok tự động hàng ngày / chuỗi đêm**:
   - Gỡ bỏ hoàn toàn Phase Reg TikTok khỏi các pipeline tự động ngầm. Không tự ý kích hoạt reg TikTok khi chưa có chỉ định cụ thể.

### B. 3 Cổng Kiểm Tra An Toàn (3-Gate Safe Trigger):
Bất kỳ Event-Driven Watchdog nào chạy sau ca cũng bắt buộc kiểm tra 3 cổng:
1. **Gate 1 - Session Completion Gate**:
   - Đọc `D:/Taadaa/runtime/kibe/cron-state/feed_session_reported.json`.
   - Bắt buộc kiểm tra session ca tương ứng của ngày hôm nay đã được ghi nhận: `<today>_ca1_phien2` (cho ca sáng) hoặc `<today>_ca2_phien2` (cho ca trưa).
2. **Gate 2 - Fleet Idle & Lock Gate**:
   - Kiểm tra `psutil`: Tuyệt đối không còn tiến trình nuôi feed nào đang chạy (`multi_machine_feed_session`, `run-feed-session.ps1`, `run_follow`).
   - Kiểm tra thư mục device lock (`C:/Users/Kibe/AppData/Local/automation-core/device-locks`): Không còn máy nào bị giữ lock.
3. **Gate 3 - Idempotency Ledger Gate**:
   - Ghi nhận trạng thái hoàn thành vào state file riêng (ví dụ `post_morning_gmail_2fa_state.json` hoặc `post_noon_chain_state.json`).
   - Nếu ngày hôm nay đã chạy thành công $\rightarrow$ Im lặng thoát (Silent Skip), không chạy lặp lại.
