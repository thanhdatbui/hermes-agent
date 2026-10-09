# Fast Swipe Like Rate Dilution & Cadence Calibration (2026-10-03)

## 1. Hiện tượng & Phân tích hiện trường
- **Triệu chứng:** Trong các ca chạy nuôi acc (`multi-machine-feed-session`), dù cấu hình tỷ lệ like cho Bạn bè (Friends) là 65% và Đang follow (Following) là 35%, số liệu đối soát thực tế toàn ca từ 80 máy (`run_manifest.json` / `summary.txt`) luôn chỉ loanh quanh **10% – 14%** (ngang ngửa tab For You).
- **Nguyên nhân gốc rễ (Root Cause):**
  1. **Hiệu ứng pha loãng (Dilution Effect) của Fast Swipe:**
     - Cơ chế Fast Swipe xen kẽ lướt nhanh 2–4 video không dump XML và **hoàn toàn không thả tim (like = 0%)** để tiết kiệm CPU và tránh giật lag.
     - Tỷ lệ like chỉ được tính trên số ít video Deep Inspect (khoảng ~28% tổng video).
     - Công thức thực tế: `Tỷ lệ like thực tế = Tỷ lệ like Deep Inspect × Tỷ lệ video Deep Inspect`.
     - Với Friends: `65% × 28% ≈ 18%` (thực tế log: 13.6% – 23.3%).
     - Với Following: `35% × 28% ≈ 10%` (thực tế log: 10.3% – 11.3%).
  2. **Tỷ lệ phân bổ tab (70/15/15):** Một phiên chỉ 16–22 video, chu kỳ bốc thăm đổi tab 3–8 video khiến hơn 80% số máy không hề ghé thăm tab Following hay Bạn bè suốt phiên.

## 2. Giải pháp hiệu chỉnh giữ nguyên Fast Swipe (2026-10-03)
Không tắt Fast Swipe (để giữ tải CPU máy nhẹ), mà cân bằng lại nhịp và tỷ lệ:
1. **Nâng tỷ lệ Deep Inspect Like Rate:**
   - Tab Bạn bè (Friends): `_deep_like_rate = 85` (từ 65).
   - Tab Following: `_deep_like_rate = 65` (từ 35).
   - `DEFAULT_FEED_LIKE_RATES`: Following = 55, Friends = 75.
   - Phân phối mềm: Following = (45, 65), Friends = (65, 85).
2. **Thu ngắn chu kỳ Fast Swipe cho tab Friends & Following:**
   - Tại `feed_swipe_smoke.py`: Khi ở `FEED_TYPE_FRIENDS` hoặc `FEED_TYPE_FOLLOWING`, nạp lại `videos_until_deep_inspect = random.randint(1, 2)` thay vì `random.randint(2, 4)`.
   - Kết quả: Cứ lướt nhanh 1–2 video là có 1 video xem kỹ + thả tim, đưa tỷ lệ like thực tế lên **~50% – 60%** cho Bạn bè và **~35% – 45%** cho Following.
