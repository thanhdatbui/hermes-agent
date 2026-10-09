# Chống Nhả Follow TikTok: Natural Re-entry, Xem Video Follow Trực Tiếp & Cadence Spot-Check

## 1. Bản chất sự cố "Nhả liền (0 lượt) - Anchor bị nhả sau vuốt"
- **Hiện tượng thực tế (12/09/2026):** 27/80 máy tại Row 2 bị báo "Nhả liền (0 lượt - anchor bị nhả sau vuốt)" ngay ở lượt follow đầu tiên, mặc dù đã ngâm Cooldown lũy tiến 5 ngày (từ 07/09 đến 12/09).
- **Nguyên nhân gốc rễ (Bot Signature):**
  - Trong luồng cũ, ngay sau khi tap Follow (cả Anchor lẫn nick trong danh sách), bot lập tức gọi `pull_to_refresh_profile` (vuốt kéo từ trên xuống 3.5s để reload trang cá nhân) và dump UI kiểm tra nút.
  - Người dùng thật **không bao giờ** vừa bấm follow ai cũng vuốt kéo reload lại profile để xem có bị nhả không.
  - Thuật toán chống bot của TikTok nhận diện hành vi `tap Follow → kéo reload` là bot signature lộ liễu và kích hoạt shadow-drop lượt follow tại chỗ.
  - Tăng cooldown (48h, 96h, 7 ngày) **hoàn toàn không giải quyết được** nếu vẫn giữ hành vi vuốt reload máy móc.

## 2. Đối chiếu thực tế với script gốc GemPhoneFarm
- **Nguồn phân tích:** `D:\Taadaa\tiktok-follow\data\TIKTOK-FLOW-TÌM-KIẾM-Thành-đạt_decrypted.json` (389 nodes).
- **Khác biệt cốt lõi:**
  1. **Không hề có Pull-to-refresh:** GemPhoneFarm bấm follow xong là tiếp tục lướt video hoặc thoát ra nick khác, không kéo reload để soi nút.
  2. **Cuộn xem và xem video thật:**
     - Các node 138, 139, 140, 274 cuộn trang profile (`startY: 1859 -> endY: 598`, duration 750ms).
     - Node 259, 260 chọn ngẫu nhiên cover video trên profile (`com.ss.android.ugc.trill:id/cover`).
     - Node 299-314 xem video trong 10s đến 26s, thả tim ngẫu nhiên.
  3. **Độ trễ biến thiên tự nhiên (Jitter):** Delay 1.8s - 5.6s giữa các hành động, không dùng delay đều nhịp.

## 3. Quy trình chuẩn cho Anchor: Xem hết video rồi Follow trực tiếp trên video
- **Quy tắc:** Tương tự như luồng lướt feed (`feed_swipe_smoke.py: _maybe_follow_video`), bot luôn **xem hết thời lượng video** rồi mới bấm Follow.
- **Các bước thực hiện:**
  1. Search Anchor (@uid) → Vào Profile Anchor.
  2. Nếu Anchor chưa follow:
     - Cuộn nhẹ trang profile xuống dưới xem lướt các video.
     - Mở 1 video bất kỳ trên profile Anchor.
     - **Xem hết video hoặc xem đủ 8–15 giây** (random dwell time). Có thể thả tim ngẫu nhiên (30% - 50%).
     - **Bấm nút FOLLOW trực tiếp trên màn hình video** (dấu cộng đỏ hoặc nút Follow cạnh avatar).
     - Chờ 1–2 giây cho TikTok đồng bộ.
     - **Bấm BACK ra trang cá nhân của Anchor.**
  3. **Xác thực tự nhiên (Natural Re-entry):**
     - Khi back từ màn hình video ra profile Anchor, TikTok tự động render lại nút trạng thái mới nhất từ server mà **không cần pull-to-refresh**.
     - Nếu nút là `Đã follow` / `Bạn bè` / `Nhắn tin`: Follow Anchor thành công → Tiến hành mở tab Following.
     - Nếu nút vẫn là `Follow` đỏ: Bị TikTok drop follow → Dừng session ngay (bảo vệ nick).
  4. Nếu Anchor không có video: Cuộn profile, dừng nghỉ 3-5s rồi mới bấm follow trên profile → back ra search rồi vào lại.

## 4. Quy trình trong List Following: Tận dụng `_path_b_verify` & Cadence Spot-Check (3–5 nick)
- **Tận dụng `_path_b_verify` có sẵn:** Bấm follow trên row của list → Bấm vào nick mở profile ra xem nút (không kéo reload) → Back về list.
- **Cadence Spot-check (Claude Opus recommendation):**
  - **Lượt #1 (Canary):** Bắt buộc chạy `_path_b_verify` để bắt ngay các tài khoản đã bị cờ từ trước (chi phí phát hiện = 0).
  - **Từ lượt #2 trở đi:** Áp dụng bước nhảy thích ứng **3–5 nick** (cap 5, có jitter ±1) mới vào profile verify 1 lần.
  - Các lượt ở giữa: Tin tưởng kết quả tap local nếu nút đã đổi trạng thái, tiếp tục follow nick kế tiếp để giữ tốc độ và tránh lộ bot.
  - Nếu bất kỳ lần spot-check nào phát hiện bị nhả: Dập tắt session ngay (`FOLLOW_FAILED`), không cố bấm tiếp.
