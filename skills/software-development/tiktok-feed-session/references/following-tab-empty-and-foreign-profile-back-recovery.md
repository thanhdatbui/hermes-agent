# Phục hồi lỗi kẹt Tab Following trống, Profile người khác và Profile Preflight Mismatch

## 1. Hiện tượng & Tác động thực tế (Incident 2026-09-23)
Trong các ca nuôi lướt Feed (Row 1/Row 3), tỷ lệ fail tăng vọt lên ~28.75% (tiệm cận ngưỡng RED ALERT 30%) do dồn 3 cụm lỗi logic chính trong `tiktok-luot nuoi acc`:
1. **Kẹt `manual-needed:network` khi chuyển tab Following:** Nhiều máy (M33, M41, M70, M72, M75) lướt được vài video FYP, đến khi chuyển tab Following thì app tải trống hoặc hiện retry marker do nick ít follow / bạn bè chưa up clip mới.
2. **Kẹt trang Profile người lạ (`navigation target profile not found in XML`):** Nhiều máy (M17, M23, M25, M76) dừng ngay đầu session với 0 video lướt.
3. **Kẹt Profile Preflight do ảnh nhận diện nhầm Top-tab:** M14, M42 dừng với `known TikTok screen` dù đã đứng đúng trang cá nhân.

---

## 2. Nguyên nhân gốc rễ (Root Cause)

### A. Kẹt Tab Following trống / Network Error
- Tại `switch_{next_feed_type}_{swipe_count}_navigation_confirm`, khi tab Following/Friends gặp `manual-needed:network`, script gọi `manual_guard.record(...)` và `return finalize_feed_session_cleanup(...)` ngay lập tức.
- Điều này biến một lỗi cục bộ ở tab phụ thành lỗi chí mạng ngắt toàn bộ phiên nuôi, khiến máy chỉ đạt 3-8 video thay vì 16-22 video.

### B. Bẫy "Đã follow" trong `following_terms` & Bỏ qua KEYCODE_BACK
- Trong `python_runner/core/classifier.py`, biến `following_terms` chứa cụm từ `"Đã follow"` (`\u0110\u00e3 follow`).
- Trên app TikTok tiếng Việt, `"Đã follow"` là trạng thái của nút quan hệ bạn bè (đã theo dõi đối phương), xuất hiện trên trang cá nhân của người khác khi mở từ thông báo / gợi ý kết bạn / follow back.
- Khi dính pop-up chuyển hướng sang Profile người khác:
  1. `classify_tiktok_screen` quét thấy `"Đã follow"` -> phân loại nhầm thành màn hình `following` (Home Feed tab Following).
  2. Trong `python_runner/flows/calibrate_screens.py` hàm `navigate_to_target`, đoạn guard `is_home_or_feed` kiểm tra `current_classification.screen in {"home", "for-you", "following", "friends"}` -> đánh dấu `is_home_or_feed = True`.
  3. Khi cần điều hướng về Hồ sơ (`target=profile`), script cố ý **bỏ qua** lệnh nhấn `KEYCODE_BACK` vì tưởng app đang ở Feed chính (`navigation_back_recovery_skipped_at_home_feed`).
  4. Trang profile người khác không có thanh điều hướng đáy (Bottom Bar) chứa nút "Hồ sơ" -> script báo `navigation target profile not found in XML` và fail cả session.

### C. Profile Preflight False-positive Drift
- Tại `_profile_guard_drifted_from_profile(row)`, nếu detector hình ảnh phân loại nhầm underline phía trên thành `following` trong khi XML đã xác nhận `xml_detected_screen == "profile"`, hàm vẫn coi là drift khỏi profile và kích hoạt chuỗi re-tap vô ích, dẫn đến dừng với lý do `known TikTok screen`.

---

## 3. Giải pháp chuẩn hóa (Patch Contract)

### 1. Soft Fallback về FYP khi Tab Following/Friends lỗi mạng
- Trong `python_runner/flows/feed_swipe_smoke.py`, tại khối `if manual_guard.record(_safety_from_row(ctx, confirm)):`:
  ```python
  if next_feed_type in {FEED_TYPE_FOLLOWING, FEED_TYPE_FRIENDS} and confirm.get("detected") == "manual-needed:network":
      ctx.logger.log(
          device_id=ctx.device_id,
          account=ctx.account,
          step=f"{artifact_prefix}/switch_{next_feed_type}_{swipe_count}_network_fallback_for_you",
          action="fallback_feed_tab",
          result="warning",
          extra={"failed_target": next_feed_type, "fallback_target": FEED_TYPE_FOR_YOU},
      )
      next_feed_type = FEED_TYPE_FOR_YOU
      current_feed_type = FEED_TYPE_FOR_YOU
      confirm["status"] = ExitStatus.DEGRADED.value
      confirm["safety_status"] = "ok"
  ```
- Cho phép phiên tiếp tục lướt trên tab For You (FYP) để hoàn thành đủ chỉ tiêu video, biến lỗi P0 thành trạng thái DEGRADED chấp nhận được.

### 2. Tách nhãn nút quan hệ khỏi tab Following & Guard thoát Profile người lạ
- Trong `python_runner/core/classifier.py`:
  - Loại bỏ `"Đã follow"` khỏi `following_terms`. Chỉ giữ `"Following"`, `"Đang Follow"` đại diện cho tab trên thanh điều hướng top feed.
  - Bổ sung `"follow lại"`, `"follow back"` vào danh sách hành động nhận diện Public Profile (`_is_public_profile_screen`).
- Trong `python_runner/flows/calibrate_screens.py`:
  - Thêm cờ `is_foreign_profile` phát hiện các nút tương tác đặc trưng của profile người khác:
    ```python
    is_foreign_profile = any(
        (el.attrib.get("text") or "").strip() in {"Follow lại", "Nhắn tin", "Follow back", "Message"}
        for el in current_root.iter()
    ) if current_root is not None else False
    ```
  - Nếu `is_foreign_profile == True`, bắt buộc đặt `is_home_or_feed = False`, cho phép thực hiện chuỗi nhấn `KEYCODE_BACK` (tối đa 2 lần) để app thoát khỏi trang cá nhân người lạ và quay về Home Feed.

### 3. Ưu tiên XML khi kiểm tra Profile Preflight Drift
- Trong `_profile_guard_drifted_from_profile(row)`:
  ```python
  if _profile_identity_from_profile_attempt(row) is not None:
      return False
  attempts = row.get("attempts") or []
  if any(isinstance(att, dict) and att.get("xml_detected_screen") == "profile" for att in attempts):
      return False
  ```
  Nếu cấu trúc XML đã đọc được identity hoặc kết luận màn hình là profile chính chủ, không để kết quả phân loại hình ảnh ghi đè gây loop retap.
