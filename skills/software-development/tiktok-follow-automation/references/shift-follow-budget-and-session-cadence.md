# Đối soát Ngân Sách Follow Theo Ca và Chu Kỳ 2 Phiên (Shift Cadence & Budget Realities)

## 1. Chu kỳ vận hành 4 Ca × 2 Phiên (Shift Architecture)
Hệ thống nuôi TikTok chạy theo lịch 4 Ca × 2 Phiên/ngày phân bổ theo parity ngày:
- **Ngày lẻ:** Ca 1 (Row 1) | Ca 2 (Row 3) | Ca 3 (Row 5) | Ca 4 (Row 7).
- **Ngày chẵn:** Ca 1 (Row 2) | Ca 2 (Row 4) | Ca 3 (Row 6) | Ca 4 (Row 8).

Trong mỗi Ca gồm 2 phiên:
- **Phiên 1 (Feed-first + Follow 1):** Mở nick của Row chỉ định, lướt feed khởi động, kích hoạt Follow hook đợt 1.
- **Phiên 2 (Feed + Follow 2 + Upload):** Mở lại CHÍNH NICK ĐÓ (cùng Row), lướt feed tiếp, kích hoạt Follow hook đợt 2 hoàn tất chỉ tiêu ngày, sau đó chạy Upload hook đăng video.
- **Deduplication:** Các nick mục tiêu (target pool) đã follow ở Phiên 1 được lưu trong `follow_state_{machine}_row_{row}.json` nên Phiên 2 tự động loại trừ, không bao giờ follow trùng nick mục tiêu.

## 2. Ngân sách Follow: Cấu hình mục tiêu vs Thực tế hiện trường

### Cấu hình mục tiêu (Design Config)
- `budget_per_session`: 15 – 20 follow / phiên (khuyến nghị 15 – 18).
- `budget_per_day`: 40 (trần an toàn tối đa).
- **Target cả ca (P1 + P2):** ~30 – 35 follow / ca / nick.

### Thực tế đo đạc hiện trường (Empirical Distribution)
Dữ liệu đối soát từ `follow_state_*.json` và live runs:
1. **Nick khỏe, trust cao (Không dính lỗi/nhả):**
   - Phiên 1: 10 – 15 follow.
   - Phiên 2: 12 – 17 follow.
   - **Tổng cả ca:** Đạt **20 – 30 follow / ca** (ví dụ M04 đạt 29 follow: P1=12, P2=17).
2. **Nick bị ngắt sớm (Fail-safe activation):**
   - Đạt 1 – 6 follow ở P1, gặp hiện tượng TikTok không nhận follow hoặc reload bị mất -> Script kích hoạt ngắt phiên ngay lập tức và ghi nhận `follow_failed_date` / `cooldown_until_date`.
   - Phiên 2 tự động bỏ qua follow (`follow-released-daily-cooldown`), chỉ nuôi feed.
   - **Tổng cả ca:** 1 – 6 follow.
3. **Nick nghỉ dưỡng sinh (Organic Rest ~33%):**
   - Cứ 3 máy thì có 1 máy chỉ lướt feed, không đi follow (`organic-rest-day-pure-feed`).
   - **Tổng cả ca:** 0 follow.
4. **Trung bình chung toàn farm:**
   - Trên các nick có phát sinh follow trong ca: dao động **~8 – 14 follow / nick / ca**.

## 3. Quy tắc giải thích cho người vận hành
- Khi được hỏi nick chạy 2 phiên có phải cùng 1 nick không: Khẳng định **nick đi follow (source) là cùng 1 nick**, còn **nick được follow (target) là khác nhau hoàn toàn**.
- Khi được hỏi về budget trung bình mỗi ca: Trình bày rõ 2 tầng số liệu (Target cấu hình 30-35 vs Thực tế hiện trường ~8-14 do các cơ chế ngắt fail-safe, nghỉ dưỡng sinh và cooldown nhả follow).
