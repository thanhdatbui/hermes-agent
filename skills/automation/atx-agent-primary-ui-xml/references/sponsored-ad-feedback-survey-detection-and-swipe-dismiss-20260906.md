# Sponsored Ad Feedback Survey ("Bạn có quan tâm đến quảng..." No/Yes) Trap & Recovery (Case 133, 2026-09-06, Máy 14)

## Hiện trường & Triệu chứng
- Trên video được tài trợ (sponsored ad) của TikTok, màn hình hiển thị popup khảo sát sở thích quảng cáo (*"Bạn có quan tâm đến quảng cáo này không?"* hoặc *"Bạn có quan tâm đến quảng..."*) kèm các nút lựa chọn `[No]` / `[Yes]` hoặc `[Không]` / `[Có]`.
- Phiên lướt feed bị dừng với lỗi:
  `"popup is not in the shared TikTok allowlist; manual review required; swipe recovery (2 swipes) still stuck"`

## Root Cause
Trong repo `tiktok-luot nuoi acc`, file `python_runner/flows/benign_popup.py`:
1. Màn hình khảo sát quảng cáo khi chưa được định danh chuẩn sẽ bị classifier gán nhãn thành `GENERIC_POPUP_SCREEN` hoặc `"manual-needed:popup"`.
2. Hàm `_dismiss_feed_ad_overlay_by_swipe` chỉ coi màn hình là ad feedback khi `detected_screen == SPONSORED_AD_FEEDBACK_SCREEN`.
3. Khi `detected_screen in {"manual-needed:popup", GENERIC_POPUP_SCREEN}`, hàm tự động gán:
   `handler_id = "tiktok_shop_cta_swipe_v1"`
   và áp đặt điều kiện kiểm tra bắt buộc:
   `if handler_id == "tiktok_shop_cta_swipe_v1" and not has_tiktok_shop_buy_now_marker(before_root): return None`
4. Vì khảo sát quảng cáo không có nút "Mua ngay" (chỉ có "Bạn có quan tâm đến quảng..." và No/Yes), hàm trả về `None` $\rightarrow$ rơi xuống `_dismiss_shared_popup_via_core` $\rightarrow$ fail-closed với reason `"popup is not in the shared TikTok allowlist; manual review required"`.

## Giải pháp Chuẩn hóa 2 Tầng
1. **Tầng 1 (Direct Text Marker Detection trong `_dismiss_feed_ad_overlay_by_swipe`)**:
   - Quét text XML trước khi kiểm tra Shop CTA: nếu XML chứa text khảo sát quảng cáo (`(?i)quan tâm đến quảng cáo` hoặc `Bạn có quan tâm đến quảng`), gán `handler_id = "tiktok_sponsored_ad_feedback_swipe_v1"` và bỏ qua yêu cầu `has_tiktok_shop_buy_now_marker` để cho phép bounded swipe thoát video ad.
2. **Tầng 2 (Đăng ký typed handler trong `benign_popup_registry.py`)**:
   - Khai báo handler `sponsored_ad_feedback_survey`:
     - Matcher: Tìm node chứa text `(?i)quan tâm đến quảng cáo` hoặc `Bạn có quan tâm đến quảng` kèm button `No`/`Yes`.
     - Dismisser: Tìm và tap nút `No` (hoặc `Không`), nếu không tap được thì thực hiện 1 bounded swipe up chuyển video feed.
3. **Quy tắc trích xuất hiện trường (Anti-Timeout)**:
   - CẤM TUYỆT ĐỐI dùng `grep -rn` hoặc `find` quét thư mục `.ai-runs/` hoặc toàn bộ `python_runner/` vì dung lượng log lịch sử và cache quá lớn sẽ gây timeout 900s. Chỉ dump UI XML qua ATX session (`capture_atx_session_ui`) và screencap trực tiếp.
