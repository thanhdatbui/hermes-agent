# Decouple Reg TikTok & Post-Noon Chained Pipeline (Gmail + 2FA) (2026-09-13)

## 1. Bối cảnh & Quyết định Vận hành (User Directive 13/09/2026)
- **Vấn đề cũ**: Cronjob `night-chain-reg-pipeline` (ID: `38ea60c09825`) chạy vào mốc giờ cố định 01:00 AM gồm chuỗi 3 Phase: Reg Gmail -> Reg TikTok -> Add 2FA TikTok.
- **Hạn chế**:
  1. Giờ cố định 01:00 AM đè vào thời gian Ca 4 (Phiên 1 00:00, Phiên 2 01:30), gây tranh chấp device lock và chiếm dụng tài nguyên máy khi ca nuôi đang diễn ra.
  2. Việc đưa Reg TikTok vào chuỗi batch ngầm không còn phù hợp, vì logic tài khoản đã chuyển sang on-demand hoặc bổ sung theo Row cụ thể.
- **Quyết định mới từ User**:
  1. **BỎ HẲN Reg TikTok** khỏi chuỗi tự động.
  2. **Bỏ lịch chạy đêm cố định 01:00 AM**: Tạm dừng (pause) hoặc xóa cronjob `night-chain-reg-pipeline`.
  3. **Chuyển sang chạy cuốn chiếu ngay sau Ca Trưa (Post-Noon Rolling Pipeline)**:
     - Ca trưa (Phiên 1: 12:00, Phiên 2: 14:00) kết thúc vào khoảng 14:40 – 15:00.
     - Khung giờ từ 15:00 đến 18:00 (trước khi Ca 3 bắt đầu lúc 18:00) là khoảng đệm rảnh rỗi 3 tiếng lý tưởng nhất trong ngày.
     - Thiết bị đã hoàn tất ca trưa, quay về màn hình HOME, nhả toàn bộ lock.

---

## 2. Kiến trúc Chạy Cuốn Chiếu (Event-Driven Watchdog)
Thay vì chạy bằng cron hẹn giờ cứng (Fixed-Time Scheduler), pipeline vận hành theo mô hình Watchdog canh nhịp rảnh:

```
[Ca Trưa: Phiên 2 (14:00) Kết Thúc]
                 │
                 ▼
[Triple-Gate Preflight: 14:45 - 17:00]
  1. Process Gate: feed runner subprocess == 0
  2. Device-Lock Gate: C:\Users\Kibe\AppData\Local\automation-core\device-locks rỗng
  3. Idempotency Gate: Chưa chạy ngày hôm nay (ledger check)
                 │
                 ▼
[PHASE 1: REG GMAIL] (run_all.ps1)
  • Lọc cooldown >= 4-5 ngày
  • Deduplicate proxy: tối đa 1 máy / cặp proxy
  • Timeout tối đa 60 phút
                 │
                 ▼
[PHASE 2: ADD 2FA TIKTOK / GMAIL]
  • Chạy batch 2FA cho các tài khoản đủ điều kiện
  • Quản lý device lock độc quyền từng máy
                 │
                 ▼
[TỔNG KẾT & BÁO CÁO TELEGRAM]
  • Gửi 1 tin báo cáo duy nhất về Telegram (format chuẩn: Tổng máy, Success, Fail kèm mã lỗi)
  • Bắt buộc ghi nhận ledger hoàn thành ngày để không chạy lại
```

---

## 3. Quy chuẩn An toàn & Ranh giới Thời gian (Buffer Time Guard)
1. **Ranh giới cứng (Hard Deadline)**: Toàn bộ pipeline bắt buộc phải hoàn tất hoặc tự động dừng trước **17:15** (cách Ca 3 lúc 18:00 ít nhất 45 phút) để không bao giờ tranh chấp với ca tối.
2. **Cơ chế Idempotency**:
   - Ghi nhận state tại `D:\Taadaa\runtime\kibe\cron-state\post_noon_chain_history.json`.
   - Mỗi ngày chỉ kích hoạt đúng 1 lần. Nếu đã kích hoạt thành công trong ngày thì các tick sau tự động im lặng (silent skip).
3. **Phân loại lỗi và Báo cáo**:
   - Tuân thủ Fleet Error Budget: Lỗi lẻ tẻ đơn máy được gom vào báo cáo tổng kết, không réo còi Farm Alert giữa chừng.
   - Báo cáo ngắn gọn không emoji:
     ```text
     [BÁO CÁO CHUỖI SAU CA TRƯA] Reg Gmail -> Add 2FA
     - Thời gian: 15:05 -> 16:10 (65 phút)
     - Phase 1 (Reg Gmail): Tổng máy: X | Success (Y): ... | Fail (Z): ...
     - Phase 2 (Add 2FA): Tổng máy: A | Success (B): ... | Fail (C): ...
     ```
