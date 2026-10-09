# Quy Tắc Cấm Follow Tự Nhiên & Thẻ Đề Xuất Trong Phiên Lướt Feed (2026-10-07)

## 1. Bản Chất Vấn Đề
- Trong phiên nuôi nick lướt Feed (`feed-session-smoke` / `multi-machine-feed-session`), TikTok thường xuyên chèn:
  1. **Thẻ đề xuất tài khoản / bạn bè trên Feed:** Hiển thị nút "Follow lại" / "Theo dõi lại" (id `com.ss.android.ugc.trill:id/fij`, `cv4`).
  2. **Popup gợi ý bạn bè / Gợi ý follow:** Hiển thị danh sách tài khoản kèm nút Follow (xử lý trong `dismiss_follow_friends_suggestion_popup`).
- Nếu script tự động bấm nút "Follow lại" hoặc tap follow trong popup:
  - Đây là thao tác "bấm mù" (không có verify bằng pull-to-refresh xem server TikTok có nhận hay nhả lại).
  - Làm cháy hạn mức hành vi (burst velocity limit) của tài khoản TikTok.
  - Khi tài khoản chuyển sang chạy **Follow chéo** (`tiktok-follow`), TikTok kích hoạt silent-block ngầm khiến hàng loạt nick anchor bị nhả về 0.
  - Làm lệch đối soát của Watchdog (báo có follow tự nhiên nhưng Web tăng 0).

## 2. Quy Tắc Chuẩn Hóa Bắt Buộc
- **KHÓA 100% FOLLOW TRONG TOÀN BỘ PHIÊN LƯỚT FEED:**
  - Không phân biệt nick già hay nick non, không phân biệt đủ điều kiện hay chưa đủ điều kiện.
  - Gặp thẻ đề xuất `follow_back_suggestion`: **LUÔN LUÔN tìm và bấm nút "Không quan tâm"** (`resource-id: cv6` / text `Không quan tâm`) để ẩn thẻ lướt qua.
  - Gặp popup gợi ý `follow_friends_suggestion_popup`: **Đặt cứng `follow_limit = 0`**, chỉ tìm nút X / Mũi tên Back / nút đóng ngữ nghĩa để thoát popup về màn hình Feed.
- **PHÂN VAI ĐỘC QUYỀN:**
  - Repo `tiktok-luot nuoi acc`: CHỈ làm nhiệm vụ lướt feed thuần túy (xem video, thả tim, đọc comment, dọn popup).
  - Repo `tiktok-follow`: ĐỘC QUYỀN thực hiện hành vi Follow (có quản lý budget state, ngâm video, pull-to-refresh profile để kiểm tra nhả follow).
