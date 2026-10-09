# Sponsored Ad Feedback Survey ("Bạn có quan tâm đến quảng..." No/Yes) Trap & Recovery (2026-09-06)

## Hiện trường & Triệu chứng (Máy 14, Case 133)
- Trên feed TikTok xuất hiện khảo sát độ quan tâm quảng cáo của video tài trợ (*"Bạn có quan tâm đến quảng cáo này không?"* hoặc *"Bạn có quan tâm đến quảng..."*) với nút `No` / `Yes` hiển thị đè lên feed hoặc thanh navigation.
- Phiên lướt feed bị dừng với lỗi:
  `"popup is not in the shared TikTok allowlist; manual review required; swipe recovery (2 swipes) still stuck"`

## Root Cause
Trong `python_runner/flows/benign_popup.py`:
1. Hàm `_dismiss_feed_ad_overlay_by_swipe` phụ trách vuốt bỏ qua ad overlay khi gặp `SPONSORED_AD_FEEDBACK_SCREEN`.
2. Tuy nhiên, khi screen classifier chưa gắn nhãn `SPONSORED_AD_FEEDBACK_SCREEN` (mà bị phân loại thành `GENERIC_POPUP_SCREEN` hoặc `"manual-needed:popup"` do dùng resource-id lạ như `t4l`/`t4k`, `tes`/`ter`), nhánh `elif detected_screen in {"manual-needed:popup", GENERIC_POPUP_SCREEN}:` mặc định gán:
   `handler_id = "tiktok_shop_cta_swipe_v1"`
   và đòi hỏi:
   `if handler_id == "tiktok_shop_cta_swipe_v1" and not has_tiktok_shop_buy_now_marker(before_root): return None`
3. Vì ad survey không có nút "Mua ngay", hàm trả về `None`, rơi xuống `_dismiss_shared_popup_via_core`. Core allowlist không có popup này nên báo `manual-needed` và dừng phiên.

## Giải pháp chuẩn hóa
1. **Trong `_dismiss_feed_ad_overlay_by_swipe` (`benign_popup.py`)**:
   - Kiểm tra trực tiếp nội dung text XML (`has_sponsored_ad_feedback_marker(before_root)` hoặc chứa regex `(?i)quan tâm đến quảng cáo` / `Bạn có quan tâm đến quảng`):
   - Nếu phát hiện marker này, gán `handler_id = "tiktok_sponsored_ad_feedback_swipe_v1"`, bypass điều kiện `has_tiktok_shop_buy_now_marker` và thực hiện 1 bounded swipe qua video ad.
2. **Trong `benign_popup_registry.py`**:
   - Đăng ký handler `sponsored_ad_feedback_survey`:
     - Matcher: Tìm text `(?i)quan tâm đến quảng cáo` hoặc `Bạn có quan tâm đến quảng` kèm button `No` / `Yes` hoặc `Không` / `Có`.
     - Dismisser: Tìm và tap nút `No` (hoặc `Không`), hoặc gửi bounded swipe up để chuyển sang video tiếp theo.
3. **CẤM quét đĩa rộng**:
   - TUYỆT ĐỐI KHÔNG dùng `find` hay `grep -rn` quét `.ai-runs/` hoặc `python_runner/` vì chứa hàng ngàn runs lịch sử và cache dẫn đến timeout 900s.
