# TikTok Follow Drop (Nhả Follow), 48h Cooldown & Recovery Dynamics

## 1. Bản chất hiện tượng Nhả Follow trên Farm
Khi tài khoản TikTok thực hiện follow chéo (Mode 1 / Mode 2), TikTok áp dụng 2 cơ chế hạn chế chính:
1. **Rate-limit / Quota tạm thời (Transient Threshold):** Tài khoản hoạt động bình thường ở chu kỳ trước (follow 15–40 target), nhưng khi đạt hạn mức tích lũy trong chu kỳ hiện tại, TikTok tự động nhả (drop) follow ở các target tiếp theo.
2. **Shadowban / Action-block sâu (Persistent Release):** Tài khoản bị phạt nghiêm ngặt, bị nhả ngay từ target đầu tiên (0–4 follow) liên tiếp qua nhiều chu kỳ (>= 3 chu kỳ liên tiếp, ví dụ M9, M17, M18, M27, M52, M61).

## 2. Thống kê tỷ lệ hồi phục thực tế qua chu kỳ 48h
- **Nhóm hồi phục nhanh (25% – 50%):** Sau 48h cooldown (nghỉ 1 ca Chẵn/Lẻ), TikTok gỡ cờ phạt tạm thời và cho phép tài khoản tiếp tục follow bình thường với hạn mức 20–40 follow/ngày (ví dụ M35, M67).
- **Nhóm dính nhả mới:** Các tài khoản trước đó follow bình thường có thể bị nhả ở chu kỳ kế tiếp khi chạm ngưỡng theo dõi.
- **Nhóm lì đòn (5% – 10%):** Bị nhả liên tục 3–4 chu kỳ dù đã nghỉ đủ 48h.

## 3. Quy tắc vận hành Cooldown
- **Giữ nguyên chu kỳ 48h mặc định:**
  - Tận dụng tối đa tỷ lệ 25% – 50% nick hồi phục sớm để không bỏ lỡ quota follow hàng ngày.
  - Cơ chế Fail-Fast (kiểm tra anchor ngay target đầu) đảm bảo nếu bị nhả sẽ dừng session ngay (`FOLLOW_FAILED`), không spam tiếp và không làm tăng rủi ro cho tài khoản.
- **Chiến lược Backoff cho nhóm lì đòn (>= 3 chu kỳ liên tiếp):**
  - Đưa vào danh sách blacklist nghỉ sâu 4–6 ngày (bỏ qua 1–2 ca tiếp theo) thay vì tiếp tục thử mỗi 48h.
