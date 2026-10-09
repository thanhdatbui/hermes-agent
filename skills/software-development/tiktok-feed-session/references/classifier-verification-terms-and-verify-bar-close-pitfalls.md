# Pitfall: False-positive Captcha/Verification vs verify-bar-close & Feed Captions

## 1. Caption video chứa từ khóa xác minh trên Feed (False Positive Challenge)
Trong `classifier.py`, việc kiểm tra `manual_challenge_terms` (ví dụ "xác minh", "kiểm tra bảo mật") có thể bắt nhầm văn bản caption hoặc mô tả video trên feed `for-you` nếu không kiểm tra feed controls trước.
- **Biểu hiện:** Feed bình thường nhưng có video mang caption chứa từ khóa xác minh bị nhận nhầm thành `manual-needed:verification`.
- **Cách xử lý:** Guard bằng `_has_feed_detail_controls(elements)`:
  ```python
  if not _has_feed_detail_controls(elements) and any(_is_manual_challenge_match(value) for value in [*texts, *descs]):
      return ScreenClassification(
          screen="manual-needed:verification",
          confidence=0.85,
          reasons=["manual_challenge/verification text present"],
          manual_needed=True,
      )
  ```

## 2. Rủi ro khi gỡ bỏ hoặc sửa khối `verify-bar-close`
`verify-bar-close` thường xuất hiện trong thanh header của webview/dialog xác minh bảo mật của TikTok.
- Trong `classifier.py`, khối `verify-bar-close` phân loại màn hình thành `manual-needed:manual_challenge`.
- Nếu gỡ bỏ hoặc refactor `verify-bar-close` mà không cập nhật các rule liên quan, các fixture test hiện tại (như `test_captcha_without_close_x_remains_manual_challenge`, `test_manual_challenge_manual_needed_with_captcha_text`, `test_manual_challenge_manual_needed_with_verify_text`) sẽ rơi vào các nhánh phân loại khác (`manual-needed:login` hoặc `manual-needed:verification`), gây fail suite unit test.
- Khi refactor selector popup / captcha, luôn chạy toàn bộ suite `python -m pytest python_runner/tests/test_classifier.py` để đảm bảo test coverage đạt 100%.
