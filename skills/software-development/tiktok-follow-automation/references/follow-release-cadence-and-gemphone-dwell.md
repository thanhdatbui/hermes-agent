# Kiến Trúc Chống Nhả Follow & Cadence Verification (Tư Vấn Claude CLI & GemPhoneFarm 12/09/2026)

## 1. Bản Chất Kỹ Thuật Hiện Tượng "Nhả Liền (0 Lượt)"

### Chống suy đoán vội vàng (Anti-Speculation):
- **Cơ chế nhả tồn tại ở mọi lượt follow:** Trong `verify_follow.py` (`_confirm_not_released`), bất kể là Anchor hay nick trong danh sách Following, sau khi bấm nút và hiện `followed`, hệ thống đều kéo reload để kiểm tra nút.
- **Bỏ qua Anchor không giải quyết được vấn đề:** Nếu tài khoản đã bị TikTok shadow-ban tương tác (action-block), thì ngay nick đầu tiên trong danh sách Following cũng sẽ bị TikTok drop và dập tắt session.
- **Cooldown lũy tiến không tự hồi phục:** Dữ liệu thực nghiệm 69 máy cho thấy sau 5 ngày ngâm cooldown (07/09 đến 12/09), 27 máy vừa chạy lại vẫn bị nhả ngay lượt đầu tiên. Tăng cooldown (48h/96h/7 ngày) không giải quyết được nếu không thay đổi hành vi tương tác.

## 2. Tử Huyệt Bot Signature: `Pull-to-refresh`

- **Hành vi bất thường:** Người dùng thật không bao giờ vừa bấm follow ai cũng kéo reload trang cá nhân (3.5s) để xem có bị nhả không.
- **Tác hại:** Việc lặp lại `tap Follow -> pull-to-refresh 3.5s -> dump UI` 15-18 lần liên tiếp trong một phiên là chữ ký bot lộ liễu khiến thuật toán TikTok kích hoạt drop follow ngay tại chỗ.
- **Giải pháp: Natural Re-entry (Thay thế hoàn toàn Pull-to-refresh):**
  - Khi cần kiểm tra trạng thái server: Điều hướng ra ngoài (back ra feed/search 1-2s) rồi mở lại profile đó (`reload_fn`) để đọc trạng thái server thật.
  - Loại bỏ hoàn toàn thao tác vuốt kéo reload tại chỗ (`pull_to_refresh_profile`).

## 3. Cadence Spot-Check (Nhịp Kiểm Tra Định Kỳ 3–5 Nick)

Trong một phiên 15–18 lượt follow:
- **Lượt #1 (Canary):** BẮT BUỘC kiểm tra qua Natural Re-entry. Bắt ngay các nick đã bị gắn cờ từ trước với chi phí gần bằng 0 (dừng session ngay, không đốt thêm nick).
- **Lượt #2 trở đi:** Bỏ qua re-entry, chấp nhận trạng thái nút local tại chỗ để giữ tốc độ và không làm lộ hành vi.
- **Nhịp Spot-check (Adaptive 3..5, cap 5):** Chỉ kích hoạt Natural Re-entry kiểm tra ngẫu nhiên sau mỗi **3 đến 5 nick** (jitter +-1, tối đa không quá 5 nick).
- **Lý do chọn 3–5 thay vì 5–7:** Tránh worst-case khi nick bị chặn giữa chừng thì không bị bấm cố quá nhiều (cap 5 giúp chỉ lọt tối đa 4 nick trước khi phát hiện và ngắt session).

## 4. Pre-Follow Engagement (Hành Vi Người Thật Từ GemPhoneFarm)

Đối chiếu từ workflow gốc `TIKTOK-FLOW-TÌM-KIẾM-Thành-đạt_decrypted.json` (389 nodes):
- **Không bấm Follow ngay khi vào profile:**
  1. Cuộn trang nhẹ 1 lần (`swipe up`).
  2. Bấm mở ngẫu nhiên 1 video trên lưới (`id/cover`).
  3. Dwell time biến thiên: Xem video từ **4 đến 11 giây** (randomize, không để cố định để tránh tạo pattern).
  4. Thả tim ngẫu nhiên (tỷ lệ 30% - 50%).
  5. Back về profile rồi mới bấm **Follow**.
