# Quy Chuẩn AI Auto-Recovery Code-First & Danh Mục Rules Popup Farm (19/08/2026)

## 1. Triết Lý & Quy Trình 5 Bước AI Auto-Recovery Code-First
Khi thiết bị gặp lỗi dừng phiên (`manual-needed`):
1. **Giữ nguyên hiện trường**: Bắn alert kèm ảnh banner đỏ `[MAY XX] - HH:MM DD/MM` về Farm Alerts. Giữ nguyên màn hình và XML tại thời điểm kẹt.
2. **AI phân tích lỗi thật & BẮT BUỘC VÁ SCRIPT TRƯỚC (Code-First)**:
   - AI đọc ảnh + XML hiện trường.
   - **Tuyệt đối CẤM chỉ gửi lệnh ADB chữa cháy tạm thời mà không vá code**.
   - Bắt buộc bổ sung Rule hoặc viết Handler hoàn chỉnh vào codebase (`feed_swipe_smoke.py` hoặc `benign_popup.py`).
   - Quy tắc an toàn bảo vệ farm bắt buộc trong prompt Vision:
     - CẤM factory reset, CẤM clear app data (`pm clear`), CẤM gỡ cài đặt app.
     - CẤM tap vào vùng nhạy cảm (OTP, mật khẩu, xóa tài khoản, thanh toán, liên kết ngân hàng).
     - Chỉ viết handler khi có đủ bằng chứng rõ ràng từ XML/ảnh; nếu không xác định được màn hình thì để code_patch rỗng và giữ hiện trường.
3. **Test trực tiếp hàm vừa code tại hiện trường kẹt**:
   - Nạp đoạn code vừa sửa chạy thử ngay tại trạng thái đang kẹt để kiểm chứng vượt lỗi (CẤM chạy lại từ đầu).
4. **Audit qua Plan-Review độc lập & Pytest**:
   - Gọi Model Plan-Review (`gpt-5.6-terra` / `plan-review` qua 9Router HTTP API) kiểm tra diff an toàn logic.
   - Nhận verdict `APPROVED` -> Chạy `pytest` -> Commit & Push Git đồng bộ 80 máy.
5. **Báo cáo nghiệm thu (Tin nhắn 2)**:
   - Gửi tin nhắn kết quả vào Farm Alerts gồm Hướng sửa & Kết quả thực tế.

---

## 2. Danh Mục Các Blind Popup Rules Đã Chuẩn Hóa Trên Farm

| Tên Rule | Selector Nhận Diện (Detection XPath / Marker) | Hành Động Xử Lý | Mục Đích |
|---|---|---|---|
| `learn_more_dialog_dismiss` | `Tìm hiểu thêm`, `Thêm vào giỏ hàng` | Tap nút `Đóng` (`tv_close`, `close_btn`, `hwn`, `e63`) | Đóng popup quảng cáo Enfagrow A+, OMO, Shop CTA. |
| `search_screen_back` | `Bạn có thể thích`, `Tìm kiếm`, `tv_search_sug_word`, `zsc` | Gửi phím `BACK` (Keyevent 4) | Thoát khỏi trang gợi ý tìm kiếm / video xem từ kết quả search về Feed. |
| `live_reward_policy_acknowledge` | `Chính sách Phần thưởng`, `Chính sách vật phẩm ảo` | Tap nút `Đóng` / `Đã hiểu` (`540, 1490`) | Xác nhận popup chính sách trong phòng Live. |
| `live_room_exit` | `live_room_container`, `Phòng LIVE`, `Bảng xếp hạng hàng ngày`, `gu4` | Dừng xem 6–14s rồi tap `X` (`close`, `e63`, `e6n`, `e68`) | Thoát phòng Livestream về Feed. **Lưu ý: Không dùng `long_press_layout` để tránh false positive video thường.** |
| `brand_product_grid_back` | `user_just_watched_btn`, `Vừa xem` | Gửi phím `BACK` | Thoát khỏi lưới sản phẩm Closeup/thương hiệu. |
| `profile_views_back` | `Lượt xem hồ sơ`, `Số lượt xem hồ sơ` | Tap `Quay lại màn hình trước` / `Đóng` | Thoát khỏi trang xem lịch sử ai đã xem profile. |
| `sponsored_ad_feedback_swipe` | `Bạn có quan tâm đến quảng cáo` | Swipe lướt qua video kế | Bỏ qua khảo sát quảng cáo mà không dừng phiên. |
| `follow_back_suggestion` | `Người mà bạn có thể biết`, `Follow lại` | Tap nút `Follow lại` | Tương tác thẻ gợi ý kết bạn trên Feed. |
| `packageinstaller_permission` | `com.google.android.packageinstaller`, `Cho phép TikTok truy cập vị trí` | Tick `do_not_ask_checkbox` + Bấm `permission_deny_button` (TỪ CHỐI) | Tự động từ chối quyền vị trí/danh bạ hệ thống an toàn. |

---

## 3. Các Chốt Chặn An Toàn Hệ Thống

1. **Chặn Telegram Alert Trong Pytest (`PYTEST_CURRENT_TEST`)**:
   - Hàm `send_farm_machine_alert` kiểm tra `PYTEST_CURRENT_TEST in os.environ` -> Bỏ qua gửi Telegram và bỏ qua spawn agent khi chạy unit test.
2. **Follow Hook Timeout & Kill Subprocess**:
   - Khi follow hook bị timeout (>15 phút) -> Gọi `exc.process.kill()` dập tắt tiến trình con Python bị treo -> Force-stop TikTok -> Gửi phím Home về màn hình chính an toàn.
3. **Bật Mặc Định `allow_benign_popup_dismiss = True` Trong Multi-Machine**:
   - `multi_machine_feed_session.py` tự động kích hoạt cờ `allow_benign_popup_dismiss = True` cho các child context để thiết bị tự động vượt qua các popup quyền hệ thống Android an toàn mà không bị dừng phiên oan.
