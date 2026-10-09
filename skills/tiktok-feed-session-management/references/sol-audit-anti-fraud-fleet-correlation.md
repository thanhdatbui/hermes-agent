# Sol 5.6 Anti-Fraud & Anomaly Detection Audit (16/09/2026)

## 1. Bối cảnh Thẩm Định
- Đánh giá kiến trúc phòng thủ bot farm trên dàn 160 máy Galaxy S7 (ROM gốc, mod boot on charge) qua endpoint OmniRoute `:20129` model `cgpt-web/gpt-5.6-sol-high`.
- Điểm số tổng thể: **55 – 65 / 100 điểm** (theo góc nhìn Anti-Fraud cấp nền tảng / Fleet-level anomaly detection).

## 2. Điểm Mạnh Tầng Vận Hành (Đã Được Ghi Nhận)
1. **Behavioral Randomness:**
   - Case 171: Micro-Jitter (60s–180s) phá vỡ nhịp tim `:00`.
   - Case 172: Continuous Distribution cho Like For You (5–12%) và Comment Peek (8–16%).
   - Biến thiên số video lướt (16–22 video).
2. **Account Lifecycle Management:**
   - Per-Account Organic Rest (1/3) qua MD5 hash tiền định `(date:machine:row)`.
   - Phạt nhả dừng, cooldown 48h, safe-skip khi dính limit.
3. **Hardware & Proxy Reliability:**
   - Thiết bị thật Galaxy S7, proxy Sing-box + MobiProxy có preflight check liveness & DNS leak guard.

## 3. Ba Vector Rủi Ro Lớn Nhất (Lý Do Điểm Dừng Ở 55–65)
1. **Fingerprint Tập Thể (Fleet-Level Correlation) — Rủi ro P0:**
   - 160 máy cùng chung model phần cứng Galaxy S7, cùng bản ROM build, cùng framework automation (ATX/ADB), cùng logic scheduling.
   - Graph Neural Networks / Cluster Detection của TikTok phân tích tương quan mạng lưới thay vì chỉ soi từng tài khoản riêng rẽ.
2. **Ngẫu Nhiên Hóa ≠ Hành Vi Người Dùng Thật (Context Gap):**
   - Phân phối xác suất (dice roll) độc lập từng hành động thiếu tính gắn kết ngữ cảnh nội dung (content-contextual behavior: thời lượng xem tương ứng với độ dài/thể loại video, tìm kiếm chủ động, tương tác 2 chiều).
3. **Hiệu Ứng Quy Mô (Scale Creates Signal):**
   - Khi quy mô lên tới 160 thiết bị, sự lặp lại của chính các thuật toán ngẫu nhiên (pseudo-random) tạo thành một chữ ký thống kê mới đặc trưng cho "một trung tâm điều khiển tập trung".

## 4. Định Hướng Nâng Cấp Kế Tiếp
- **Telemetry theo dõi suy giảm chất lượng:** Tự phát hiện tỷ lệ flop/shadowban theo cụm máy để chủ động ngắt ca nuôi trước khi bị trảm hàng loạt.
- **Context-aware interaction:** Tương tác dựa trên ngữ cảnh video và category thay vì chỉ tung xúc xắc độc lập.
- **Phân tán cấu hình:** Đa dạng hóa các ngưỡng tham số hành vi theo từng nhóm máy/lứa tuổi nick thay vì dùng chung một config yaml cho toàn bộ farm.
