# Xử Lý Popup Feed, Shop, Livestream, CTA, Recents & Profile Verification (19/08/2026)

## 1. Trục Vuốt An Toàn Chống Lọt Vào Shop / Livestream / Repost
- **Hiện tượng:** Khi vuốt ngón tay ở trung tâm ($X = 540 \pm 30$px) hoặc lệch phải ($X > 600$), ngón tay dễ chạm trúng:
  - Nút **Repost / Bài đăng lại** hoặc ô nhập comment ở đáy ($Y > 1750$).
  - Thẻ preview **Livestream** (chạm vào video live sẽ kích hoạt mở phòng Live toàn màn hình `LiveRoomActivity`).
  - Nút **Mua ngay / Giỏ hàng** gắn trên video hoặc thẻ sản phẩm TikTok Shop.
- **Quy tắc tọa độ vuốt:**
  - **Trục X:** Dời hẳn sang nửa trái màn hình: $X = 400 \rightarrow 480$px (trục chuẩn $X=450$, cách xa 100% cụm tương tác phải).
  - **Trục Y:** Vuốt từ $Y_1 = 1450 \rightarrow Y_2 = 620$px (tránh vùng đáy $Y > 1750$px).

## 2. Phân Tầng Xử Lý Pop-up (System Core vs Repo In-App)
User chốt quy tắc thiết kế cốt lõi:
- **Cấp Core (`automation-core`):** Quyền hệ thống (Vị trí, Danh bạ, Quyền lưu trữ, PackageInstaller) $\rightarrow$ **TẮT LIỀN LẬP TỨC (< 0.5s)** để giải phóng màn hình, chống nghẽn luồng và không để Android đánh giá app bị mất focus.
- **Cấp Repo (`tiktok-luot nuoi acc`):** Màn hình in-app, phòng Live, TikTok Shop, Bài đăng lại, Banner CTA $\rightarrow$ **DỪNG VÀI GIÂY XEM RỒI MỚI THOÁT** để mô phỏng hành vi người thật lướt xem trước khi đóng.

### Chi tiết thời gian dừng xem tự nhiên:
1. **Phòng Livestream (`live_room_exit`):** Dừng xem ngẫu nhiên **6.0 – 14.0 giây** rồi bấm nút **✕** (`id/close`, `id/e63`, `id/e6n`, `id/e68`) ở góc trên bên phải để thoát về Feed.
2. **Trang chi tiết sản phẩm / TikTok Shop (`shop_product_detail_close`):** Dừng xem **3.0 – 7.0 giây** rồi bấm nút **✕** (`id/gnl`, `id/e5w`).
3. **Bảng "Bài đăng lại" (`repost_sheet_close`):** Dừng **2.0 – 4.0 giây** rồi bấm **✕** (`id/e55`).
4. **Màn hình "Số lượt xem hồ sơ" (`profile_views_back` - Máy 58):** Nhận diện *"Số lượt xem hồ sơ"* $\rightarrow$ bấm nút `Quay lại màn hình trước` (`←`, `[24,84][144,216]`) hoặc `Đóng` (`id/llm`).
5. **Khảo sát phản hồi quảng cáo (`sponsored_ad_feedback_swipe`):** Nhận diện *"Bạn có quan tâm đến quảng cáo"* $\rightarrow$ Vuốt dứt khoát cuộn qua video tiếp theo.

## 3. Cơ Chế 2 Lớp Cho Banner CTA & Popup Lạ Chưa Định Danh
- **Lớp 1 (CTA Matcher):**
  - Nhận diện toàn bộ các biến thể CTA trên video quảng cáo (`TIKTOK_CTA_TERMS`): *"Mua ngay", "Tìm hiểu thêm", "Xem ngay", "Cài đặt ngay", "Tải ngay", "Trải nghiệm ngay", "Nhận ngay"*.
  - Tự động vuốt lướt qua video kế tiếp thay vì dừng phiên hay bấm nhầm nút Đóng.
- **Lớp 2 (Fallback 2 Lượt Vuốt):**
  - Nếu gặp bất kỳ popup lạ, modal chưa định danh (`manual-needed:popup`), hoặc blocker không dismiss được:
  - Tự động kích hoạt `_swipe_recovery_on_stuck`: Thực hiện vuốt (swipe) lướt qua **1–2 lần** để tự giải thoát màn hình trước khi rơi vào trạng thái `manual-needed`.

## 4. Whitelist Package Hệ Thống Sau Khi Bấm Từ Chối Quyền (Máy 29)
- **Vấn đề:** Sau khi dismiss hộp thoại quyền Android (như Danh bạ, Vị trí), tiến trình `com.google.android.packageinstaller` / `com.android.permissioncontroller` mất 0.2–0.5s để ẩn hoàn toàn. Hàm kiểm tra focus sau đó đọc thấy package hệ thống $\rightarrow$ báo nhầm `TikTok focus lost after contact_follow_suggestion dismiss`.
- **Giải pháp:** Whitelist các package an toàn trong `_blocked_after_close_reason`:
  - `com.android.packageinstaller`
  - `com.google.android.packageinstaller`
  - `com.android.permissioncontroller`
  - `com.android.systemui`
  - Giúp script chờ giao diện quay về TikTok mà không kích hoạt blocker dừng máy.

## 5. Xử Lý Quyền Vị Trí Ở Bước Khởi Đầu (`before_swipe` - Máy 41)
- **Vấn đề:** Popup quyền vị trí Android (`Cho phép TikTok truy cập vị trí của thiết bị này?`) xuất hiện ngay lúc mở app. Phím Back không thể tắt được popup này. Trong chuỗi kiểm tra `before_swipe`, thiếu bước gọi `_maybe_dismiss_packageinstaller_after_swipe`.
- **Giải pháp:** Bổ sung `_maybe_dismiss_packageinstaller_after_swipe` vào ngay đầu chuỗi kiểm tra `before_swipe`:
  - Tự động tick chọn checkbox *"Không hỏi lại"* (`id/do_not_ask_checkbox`).
  - Tự động tap nút *"TỪ CHỐI"* (`id/permission_deny_button`).

## 6. Khắc Phục Lỗi So Khớp Danh Tính Cuối Phiên (`verify_profile` - Máy 52)
- **Quy tắc tuyệt đối:** **CHỈ ĐỐI SOÁT THEO ID / USERNAME TRONG EXCEL (`ctx.account`)**.
- **Lý do:** Trong file Excel chỉ lưu Username/ID TikTok, không có biệt danh (Display Name).
- **Giải pháp:** Hàm `verify_profile` chỉ so sánh `ctx.account` với chuỗi `@<username>` trên UI TikTok. CẤM so khớp theo Display Name để tránh sai lệch dữ liệu.

## 7. Xử Lý Màn Hình Recents Rỗng Trên Samsung S7 (Máy 64)
- **Hiện tượng:** Khi máy không có ứng dụng chạy ngầm nào, mở Recent Apps (`keyevent 187`) sẽ hiển thị thông báo *"Không có ứng dụng đã dùng gần đây"* (node `com.android.systemui`). Script không thấy nút *"Đóng tất cả"* (Clear All) sẽ báo lỗi `clear_all button and empty-recents evidence not found`.
- **Xử lý:** Bổ sung regex nhận diện chuỗi tiếng Việt *"Không có ứng dụng đã dùng gần đây"* vào `_EMPTY_RECENTS_RE` trong `automation-core/startup.py` và `device_prepare.py` $\rightarrow$ Xác nhận trạng thái nền đã sạch, tự động gửi phím `Home` (`keyevent 3`) và tiếp tục luồng nuôi acc.

## 8. Tự Động Phục Hồi Khi Văng App Ra Launcher (`_recover_launcher_focus_lost`)
- **Nguyên nhân:** Lướt video lâu hoặc cache lớn khiến Android Low Memory Killer rớt app về `com.sec.android.app.launcher`.
- **Giải pháp:** Script tự động phát hiện mất focus $\rightarrow$ gọi `force_stop_and_relaunch_tiktok` $\rightarrow$ chờ 3.0s cho TikTok nạp lại $\rightarrow$ recapture xác nhận Feed `for-you` và chạy tiếp tục đủ số video còn lại của phiên.

## 9. Ép Chặt Quy Chuẩn Báo Cáo & Auto Recovery (User phạt 19/08)
- **Báo cáo đích danh lỗi kỹ thuật:** CẤM TUYỆT ĐỐI các câu mơ hồ như *"Dừng phiên bất thường"*, *"Gặp popup che khuất"*. Bắt buộc ghi rõ: *"Không tìm thấy @username trong Account Switcher"*, *"Kẹt popup quyền vị trí"*, *"Kẹt phòng Live"...*
- **Giữ nguyên hiện trường:** Khi lỗi, máy dừng ở đâu giữ nguyên ở đó để AI đọc UI XML/ảnh phân tích. CẤM tự ý dọn app về Home làm mất dấu vết.
- **Quy trình Fix:** Sửa code $\rightarrow$ test thử trên máy lỗi $\rightarrow$ **kích hoạt chạy tiếp tục từ hiện trường cho đến khi phiên kết thúc hoàn toàn (SUCCESS)**.
