# Xử Lý Tab Following Rỗng Cho Nick 0-Following & Thoát Kẹt Profile Người Lạ

## 1. Hiện Tượng & Root Cause (Incident 23/09/2026)
* **Hiện tượng:** Hàng loạt máy (M33, M41, M70, M72, M75...) dừng phiên sớm (3-7 swipe) với lý do `network/error/retry marker detected` / `manual-needed:network`.
* **Root Cause thực tế:**
  - Không phải mất mạng hay rớt proxy. Video trên tab "Đề xuất" (FYP) vẫn lướt mượt mà trước khi chuyển tab.
  - Các tài khoản này là nick mới reg, **`0 Đã follow`**.
  - Khi bot thực hiện nhịp chuyển tab tự nhiên sang tab "Đang follow" (Following), TikTok không có dữ liệu video để hiển thị nên hiện thông báo mặc định: `"Đã xảy ra lỗi | Vui lòng thử lại. | [Thử lại]"`.
  - Bộ phân loại màn hình `classifier.py` nhận diện chữ "Thử lại" thành `manual-needed:network`.
  - Hàm `manual_guard.record()` tại seam chuyển tab lập tức ngắt phiên fail-closed, làm hỏng tỷ lệ hoàn thành ca nuôi.

## 2. Invariant & Quy Tắc Thiết Kế (User Chốt 23/09/2026)
1. **Vẫn vào tab Following bình thường:**
   - CẤM TUYỆT ĐỐI tự ý cắt bỏ (skip) tab Following hay ép tỷ lệ về 0% ngay từ đầu.
   - Bot vẫn phải thực hiện hành vi bấm sang tab Following theo đúng tỷ lệ phân bổ tự nhiên (15%) để giữ footprint nuôi nick chuẩn.
2. **Graceful Fallback khi gặp Feed rỗng / Lỗi mạng ảo:**
   - Khi vào tab Following/Friends, nếu nhận diện màn hình rỗng hoặc dính marker `manual-needed:network` / `retry`:
     - **CẤM ngắt phiên.**
     - Ghi nhận warning telemetry: `step=switch_{next_feed_type}_{swipe_count}_empty_feed_fallback_for_you`.
     - Lập tức gọi `tap_navigation_target(ctx, _top_tab_target(FEED_TYPE_FOR_YOU))` để lùi về tab "Đề xuất".
     - Chuyển `current_feed_type` và `next_feed_type` về `FEED_TYPE_FOR_YOU`.
     - Tiếp tục lướt các video còn lại cho đến khi đủ 100% quota video của ca chạy.

## 3. Thoát Kẹt Profile Người Lạ (Foreign Profile Back Recovery)
* **Vấn đề:** Khi mở app, pop-up "Gợi ý bạn bè" hoặc vô tình chạm vào profile tác giả/người khác (`@...`). Trang này chứa nhãn "Đang follow" / "Đã follow" khiến `calibrate_screens.py` nhận diện nhầm là đang ở Home Feed và bỏ qua phím Back (`navigation_back_recovery_skipped_at_home_feed`).
* **Giải pháp:**
  - Trong `calibrate_screens.py`: kiểm tra `is_foreign_profile = any(text in {"Follow lại", "Nhắn tin", "Follow back", "Message"})`.
  - Nếu `is_foreign_profile == True`: KHÔNG ĐƯỢC coi là `is_home_or_feed`.
  - Cho phép thực thi chuỗi `KEYCODE_BACK` để lùi khỏi trang cá nhân người lạ và quay về Feed chính.

## 4. Profile Preflight Identity Guard: Ưu Tiên XML
* **Vấn đề:** Detector ảnh qua screenshot (`classification_source: image-top-navigation`) bị nhiễu vạch underline tab dưới chân, báo mismatch so với màn hình Profile dù cấu trúc XML đã ở đúng màn hình Profile chính chủ.
* **Giải pháp:**
  - Trong `feed_swipe_smoke.py::_profile_guard_drifted_from_profile`:
    - Nếu `_profile_identity_from_profile_attempt(row)` đã đọc được username/identity hợp lệ -> `return False` (không drift).
    - Nếu bất kỳ attempt nào có `xml_detected_screen == "profile"` -> `return False`.
    - Tránh kích hoạt vòng lặp re-tap (`retap_on_degraded_xml_drift`) gây trôi màn hình.
