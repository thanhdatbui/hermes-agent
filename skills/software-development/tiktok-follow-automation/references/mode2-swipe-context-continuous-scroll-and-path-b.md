# Mode 2 Follow Workflow Enhancements (2026-08-30)

## 1. Swipe Context trước Seed Search (Mode 2)
- **Vấn đề cũ:** Sau khi quay về feed (`_back_to_feed`), runner bấm icon Search ngay lập tức mà không lướt feed, làm giảm tính tự nhiên của tương tác.
- **Quy chuẩn mới:**
  - Bắt buộc thực hiện lướt `swipe_before_search` (mặc định 1–3 video) trên Feed trước khi gõ tìm kiếm UID anchor.
  - Bọc try-catch an toàn kiểu dữ liệu, clamp `0..10`, fallback an toàn `3` nếu config bị sai kiểu/tràn số/`None`/`inf`.
  - Nếu `swipe_feed` trả về `False` hoặc ném exception (lỗi kích thước màn hình / pipe ADB), fail-closed sang `MANUAL_REVIEW` để bảo vệ tài khoản.

## 2. Loại bỏ ngắt sớm `consecutive_skip >= 20` (Continuous Scroll)
- **Vấn đề cũ:** Khi gặp 20 nick ngoài farm liên tiếp, runner kích hoạt `break` ngắt sớm anchor dù bên dưới danh sách Following vẫn còn nick farm nội bộ, gây mâu thuẫn với hạn mức cuộn tìm kiếm `max_scrolls = 40`.
- **Quy chuẩn mới:**
  - Đã loại bỏ biến và điều kiện ngắt sớm `consecutive_skip >= 20`.
  - Vòng lặp cuộn tiếp tục duyệt danh sách Following của anchor cho đến khi:
    1. Đạt đủ budget follow của phiên, **HOẶC**
    2. Danh sách chạm đáy (empty surface / `_classify_follower_surface == "empty"`), **HOẶC**
    3. Đạt 5 lần cuộn rỗng liên tiếp (`idle_scrolls >= 5`), **HOẶC**
    4. Đạt giới hạn cuộn an toàn tối đa `max_scrolls = 40`.
  - Các nick ngoài farm chỉ được ghi log/skip nhẹ trong memory của phiên, không làm gián đoạn việc cuộn quét tìm nick farm nội bộ.

## 3. Xác thực Path B trực tiếp trên 100% lượt Follow (Không cần Pull-to-refresh)
- **Quy chuẩn kiểm tra nhả follow:**
  - Sau khi tap nút Follow ở danh sách hàng (Path A), runner **100% tự động bấm vào tên nick** để mở trang Profile cá nhân của nick đó (`_path_b_verify`).
  - **Không cần pull-to-refresh / swipe:** Chỉ cần dump XML trang profile vừa mở và đọc nút quan hệ (`Đang theo dõi` / `Bạn bè` / `Nhắn tin` vs `Follow`).
  - Nếu profile vẫn hiển thị `Follow`/`Follow lại` (TikTok nhả follow) $\rightarrow$ Hàm vẫn thực hiện `adapter.back()` để khôi phục UI về danh sách trước khi trả về `failed` $\rightarrow$ Ngắt phiên `FOLLOW_FAILED` ngay lập tức để bảo vệ nick. (Lưu ý: Ảnh chụp hiện trường trên Farm Alert Telegram sẽ hiển thị danh sách Following của anchor chứ không phải profile của nick, do runner đã back ra trước khi dừng).
  - Nếu profile xác nhận đã follow $\rightarrow$ Bấm phím `Back` (keyevent 4), kiểm tra danh sách Following đã khôi phục (`_on_follower_list`), rồi tiếp tục lướt follow nick tiếp theo.
  - Nếu lệnh `Back` gặp lỗi hoặc UI không khôi phục về danh sách $\rightarrow$ Chuyển sang `MANUAL_REVIEW` (Fail-Closed).

## 4. Preflight Router Proxy `interface="auto"` & Search Back Whitelist
- `follow_runner/run_follow.py` gọi `require_android_vpn(preflight_adb, required=required, interface="auto")` để hỗ trợ router Wi-Fi transparent proxy qua `wlan0` mà không bắt buộc có interface `tun0`.
- **Search Screen Back Button Whitelist (`id/bq8`)**: Trên TikTok 46.x, nút Back màn hình Search có thể đổi sang `id/bq8` (bên cạnh `id/bow`, `id/bqp`). Bắt buộc nhận diện toạ độ góc trên bên trái `(x < 250, y < 250)` để tap thoát tìm kiếm về Feed; tránh phím Back cứng vì bàn phím mềm đang mở sẽ nuốt keycode 4 dẫn tới fail `ensure_feed_for_follow`. Chi tiết xem `references/search-back-button-and-feed-return-rules.md`.

## 5. Xử lý Anchor có 0 Following (Tránh Lặp Search Lần 2)
- **Nguyên nhân gây lặp:** Khi Anchor có `0 Đã follow` / `0 Following` (`Đã follow 0` kèm hình hoạt họa rỗng), bấm vào tab sẽ mở ra màn hình rỗng không có `RecyclerView`. Nếu parser đánh giá là `invalid` (thay vì nhận diện `empty`/`zero_following`), `_open_following_tab` trả về `False`, khiến `run_mode2` kích hoạt thang phục hồi (`recover_ui` $\rightarrow$ về Feed $\rightarrow$ tìm kiếm lại anchor đúng nick đó lần thứ 2).
- **Quy tắc chuẩn:** Nhận diện số đếm `0` trên header tab hoặc màn hình empty relation surface ngay tại lần mở đầu tiên, đánh dấu `zero_following` để quay về Feed và chuyển ngay sang Anchor tiếp theo, tuyệt đối không kích hoạt retry search lại lần 2.
