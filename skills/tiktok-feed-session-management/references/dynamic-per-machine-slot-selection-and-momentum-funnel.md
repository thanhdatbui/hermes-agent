# Per-Machine Dynamic Account Allocation & 3-Tier Momentum Funnel (Chu Kỳ Nuôi 4 Ngày)

## 1. Bối cảnh & Vấn đề kiến trúc cũ
- **Chu kỳ 4 ngày (Parity 96h):**
  - Ngày 1: Row 1, 3, 5 (Cố định).
  - Ngày 2: Row 2, 4, 6 (Cố định).
  - Ngày 3: Row 7, 8 (Cố định Sáng, Trưa) + Ca 3 Tối (Động).
  - Ngày 4: Cả 3 ca Sáng, Trưa, Tối (Động - Rest Day).
- **Điểm nghẽn cũ:** `healing_selector.py` tính điểm trung bình toàn farm rồi chọn ra duy nhất 1 Row (`row_index = N`) và ép toàn bộ 80-160 máy chạy chung Row đó.
- **Hậu quả:** 
  - Kênh đang cắn đề xuất (viral/trending) bị đói video (4 ngày mới được đăng 1 video -> nguội sóng phân phối).
  - Máy có nick đi tù (dính nhả follow) không được cứu chữa kịp thời nếu Row của nó không nằm trong điểm số cao nhất farm.
  - Máy không có nick yếu lại bị ép chạy lặp lại.

## 2. Invariant Thiết Kế: Per-Machine Dynamic (Không Cào Bằng Row Toàn Farm)
Trong các ca động (**Ca 3 Ngày 3** và **cả 3 ca Ngày 4 - Rest Day**):
- **CẤM** ép toàn farm chạy chung một `row_index`.
- Mỗi máy (Worker thread của từng điện thoại) duyệt độc lập 8 slot tài khoản của chính nó (Tik 1 đến Tik 8) qua **Phễu 3 tầng ưu tiên**:

```text
[MÁY X - Duyệt 8 slot Tik 1 -> Tik 8]
   │
   ├─► TẦNG 1: NICK CẮN ĐỀ XUẤT (Momentum Acceleration) — ƯU TIÊN CAO NHẤT
   │   • Điều kiện: `is_account_boosted()` == True trong tiktok_tracker.db
   │     (Delta follower >= 20, heart >= 50, hoặc view tăng vọt 24-48h qua).
   │   • Hành vi: Lướt nhẹ + ĐĂNG VIDEO NGAY (Bypass Rest Day upload).
   │   • Kỷ luật: TUYỆT ĐỐI 0 FOLLOW để tránh rủi ro nhả follow làm gãy đà phân phối video.
   │   • Hiệu quả: Tăng tần suất lên 2 ngày/video (hoặc 1 ngày/video trong đợt viral).
   │
   ├─► TẦNG 2: NICK ĐI TÙ VÌ NHẢ FOLLOW (Healing Recovery)
   │   • Điều kiện: Đang dính cờ `follow_failed` hoặc trong active cooldown (`_is_account_follow_cooldown`).
   │   • Hành vi: Lướt feed thuần túy (0 follow, 0 upload) để xả cờ phạt và hồi trust.
   │   • Ưu tiên: Chọn slot có streak phạt cao nhất hoặc dính án gần nhất.
   │
   └─► TẦNG 3: NICK NON / YẾU (Asset Accumulation)
       • Điều kiện: Áp dụng khi máy không có nick viral và không có nick đi tù.
       • Tiêu chí: Slot có video_count < 10 (tích lũy độ dày kênh) hoặc ít video nhất.
       • Hành vi: Lướt nuôi + Đăng video tích lũy (nếu đủ điều kiện kho media).
```

## 3. Quy tắc an toàn phần cứng: Bỏ hẳn Ca 0h đêm
- Khung giờ **21:30 – 05:59** là **Dead Zone** bất khả xâm phạm:
  - Cho dàn Samsung S7 tản nhiệt, chống chai pin/phù pin/drop cổng USB ADB.
  - Khung giờ cho các cron bảo trì hệ thống: Reboot định kỳ (05:20), dọn dẹp cache TikTok (`clear-tiktok-cache.py`), backup SQLite, dọn dẹp dead-locks.
  - Video đăng 00:00 - 02:00 rơi vào giờ người dùng ngủ -> Initial test pool bị flop (thiếu tương tác tức thời).
- Mọi nhu cầu tăng tần suất đăng video cho nick viral **BẮT BUỘC** tận dụng các ca ngày (Ca 3 Ngày 3 và Ngày 4), **CẤM** mở lại Ca 0h.
