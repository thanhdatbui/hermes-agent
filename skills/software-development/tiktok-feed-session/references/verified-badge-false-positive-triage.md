# Verified Badge False Positive Triage (Huy Hiệu Đã Xác Minh)

## Hiện tượng
- Alert Telegram / runner báo `manual-needed` với lý do `verification marker detected` hoặc `manual review required`.
- Ảnh đính kèm (hoặc terminal snapshot) là màn hình Home / Launcher hoặc trang profile TikTok bình thường của một KOL / Nghệ sĩ có tích xanh.
- Đọc XML hierarchy tại `swipe_X_after` phát hiện các node dạng:
  ```xml
  <node text="JSOL" ... />
  <node text="@jsol.dreams" ... />
  <node text="" resource-id="...:id/sj6" class="android.widget.ImageView" content-desc="Huy hiệu đã xác minh" ... />
  ```

## Nguyên nhân
Trong `python_runner/core/classifier.py`, chuỗi `manual_challenge_terms` quét substring `"xác minh"`.
Chuỗi `content-desc="Huy hiệu đã xác minh"` chứa substring `"xác minh"` nên bị bắt nhầm thành màn hình thử thách bảo mật / Captcha (`manual-needed:verification`).

## Giải pháp đã triển khai
1. Định nghĩa `_VERIFIED_BADGE_TERMS`:
   - `"huy hiệu đã xác minh"`, `"tài khoản đã xác minh"`, `"verified badge"`, `"verified account"`, và các dạng UTF-8 mojibake tương ứng.
2. Kiểm tra loại trừ trước khi so khớp `manual_challenge_terms`:
   - Trong `classify_tiktok_screen()`
   - Trong `_is_account_switcher_sheet()` (cho `blocker_terms`)
3. Bổ sung unit test regression `test_verified_badge_desc_not_misclassified_as_verification` trong `test_classifier.py`.
