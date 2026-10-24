# Adaptive Biological Shift-Pool Selection (Phân Phối Ngẫu Nhiên Thích Ứng Toàn Farm)

## 1. Bản chất & Nguyên lý Thuật toán
Để phá vỡ "dấu vân tay đồng bộ" (Network Correlation / Anti-Abuse Bot Pattern) khi 160 máy cùng thức dậy chạy chung 1 Row tại các ca cố định, hệ thống phân chia 8 Row thành 3 Tổ ca sinh học (Shift Pools):
- **Ca 1 (Sáng: 06h, 08h):** `Pool {Row 1, Row 2, Row 7}`
- **Ca 2 (Trưa: 12h, 14h):** `Pool {Row 3, Row 4, Row 8}`
- **Ca 3 (Tối: 18h, 20h):** `Pool {Row 5, Row 6}` (Day 0 & Day 1); Day 2 & Day 3 chạy Dưỡng sinh tự do.

## 2. Quy Tắc Vận Hành 4 Ngày (Cycle Rules)
- **Day 0 (Ngày 1):** Mỗi máy tự bốc nick **Khỏe nhất (Rank 1)** trong Pool của ca đó để chạy.
- **Day 1 (Ngày 2):** Mỗi máy tự bốc nick **Khỏe nhì (Rank 2)** trong các nick chưa chạy của Pool.
- **Day 2 (Ngày 3):** Mỗi máy tự bốc nick **Còn lại (Rank 3)** của Pool.
- **Day 3 (Ngày 4 - Rest Day):** Toàn farm chạy Dưỡng sinh tự do theo 3 lớp phễu (Đề xuất -> Đi tù -> Nick non).

## 3. Invariants Bắt Buộc
1. **S2 bám S1 (100% Tuyệt đối):**
   - Session 2 (phiên 2 trong cùng ca) BẮT BUỘC chạy đúng nick mà Session 1 của máy đó đã chọn.
   - Trạng thái được ghi nhận tức thì vào `today_shift_sessions[ca][machine]` trong `shift_pool_cycle_state.json`.
2. **Zero Starvation (Độ phủ 100%):**
   - Sau 3 ngày đầu của chu kỳ, tất cả 8 Row của 160 máy đều phải được chạy đủ 100%, không nick nào bị bỏ đói.
   - Sang chu kỳ mới (`cycle_idx` tăng), lịch sử `cycle_history` được reset tự động.
3. **Thước đo xếp hạng sức khỏe trong Pool:**
   - **Tier 1 (Ưu tiên cao nhất):** Nick cắn đề xuất (`is_account_boosted() == True`) -> Đưa ra chạy ngay ở Day 0.
   - **Tier 2:** Nick sạch án (không dính cooldown nhả follow, trần cao, nhiều video).
   - **Tier 3 (Xếp cuối):** Nick đang dính cooldown nhả follow hoặc ít video.
