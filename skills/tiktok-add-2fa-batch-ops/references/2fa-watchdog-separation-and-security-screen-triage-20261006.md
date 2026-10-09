# Triage Phân Tách Watchdog 2FA & Màn Hình Kiểm Tra Bảo Mật TikTok (06/10/2026)

## 1. Hiện Tượng & Nghi Vấn
- **Sự cố:** Operator quan sát thấy máy Android hiển thị màn hình TikTok "Kiểm tra bảo mật" có mục "Xác minh 2 bước" (kèm icon cảnh báo), đặt câu hỏi: "Có phải cron đang chạy add 2FA TikTok hay sao mà không thấy report gửi về Telegram?".
- **Cảnh báo chống suy đoán:** Màn hình TikTok hiển thị mục "Xác minh 2 bước" KHÔNG ĐỒNG NGHĨA với việc có cron đang chạy hoặc nick đã bật 2FA thành công. Mục 2FA còn icon cảnh báo tức là tài khoản CHƯA bật 2FA.

## 2. Bản Đồ Phân Tách Các Cron Watchdog 2FA
Toàn hệ thống phân tách rõ 2 luồng 2FA với thời gian và mục tiêu hoàn toàn khác nhau:

1. **`post-morning-gmail-2fa-watchdog` (Buổi sáng 08:30 - 11:30):**
   - **Mục tiêu:** Bật 2FA Google Authenticator cho **Gmail Profiles trên GPMLogin**, TUYỆT ĐỐI KHÔNG can thiệp nick TikTok trên điện thoại.
   - **Delivery Mode:** `local` (ghi file JSON tại `D:/Taadaa/runtime/kibe/cron-state/post_morning_gmail_2fa_state.json`), **KHÔNG gửi report Telegram**.

2. **`post-noon-chain-watchdog` (Buổi chiều 14:00 - 17:00, mỗi 5 phút):**
   - **Mục tiêu:** Chuỗi cuốn chiếu **Reg Gmail (Phase 1) -> Add 2FA TikTok (Phase 2)**.
   - **Delivery Mode:** Telegram Farm Alert (`telegram:-5373649734`).
   - **Cơ chế chặn chuỗi:** Phase 2 (TikTok 2FA) chỉ được kích hoạt sau khi Phase 1 (Gmail) hoàn thành. Nếu Phase 1 fail (`lane_status: failed`, ví dụ `gmail_code: 1`), watchdog dừng lại và không kích hoạt Phase 2 $\rightarrow$ Không có report TikTok 2FA.

## 3. Quy Trình Triage Bằng Chứng Thực Tế O(1)
Khi gặp thắc mắc về cron 2FA / report:
1. **Kiểm tra giờ hiện tại:** Nếu trước 14:00, cron TikTok 2FA chắc chắn chưa tới lịch chạy.
2. **Kiểm tra State File:**
   - `D:/Taadaa/runtime/kibe/cron-state/post_morning_gmail_2fa_state.json` (Gmail GPM).
   - `D:/Taadaa/runtime/kibe/cron-state/post_noon_chain_state.json`: Xem `last_run_at`, `lane_status`, và `2fa_code`.
3. **Kiểm tra hiện trường máy qua inspect_machine:**
   - `python D:/Taadaa/tools/inspect_machine.py <N>`
   - Nếu `mCurrentFocus=null` hoặc màn hình Sleep/Dozing và không có process `run_capture_phase_b.py`, máy hoàn toàn không có worker 2FA tác động.
