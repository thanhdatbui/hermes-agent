# Benign Popup Recapture Empty/None Screen Recovery

## Vấn đề
Trong flow xử lý popup (ví dụ `_finish_add_phone_after_core_dismiss` và `dismiss_add_phone_popup` trong `flows/benign_popup.py`), sau khi click đóng popup hoặc xử lý dismiss keyboard, script thực hiện chụp lại màn hình (recapture attempt).

Nếu màn hình hiện tại chưa rơi về screen TikTok đã biết (`_KNOWN_TIKTOK_SCREENS_AFTER_ADD_PHONE`), hệ thống thiết kế một vòng lặp gửi phím `BACK` tối đa 3 lần để đưa TikTok về màn hình nhận diện được.

Tuy nhiên, nếu điều kiện kích hoạt vòng lặp chỉ kiểm tra:
```python
if after.get("detected_screen") == "unknown":
```
Khi classifier hoặc capture trả về `None`, `""`, hoặc key `detected_screen` không tồn tại, điều kiện trên sẽ đánh giá là `False`.
Hệ quả:
- Vòng lặp BACK recovery bị bỏ qua hoàn toàn.
- Flow đi thẳng tới kiểm tra focus hoặc trả về lỗi fail closed / manual review mà không hề thử ấn BACK để hồi phục.

Trong vòng lặp recovery, nếu chỉ kiểm tra:
```python
if recovered.get("detected_screen") != "unknown":
    break
```
Thì giá trị `None` hoặc `""` lại khiến vòng lặp thoát sớm (`None != "unknown"` là `True`), phá vỡ logic retry.

## Giải pháp chuẩn hóa
1. **Luôn dùng helper chuẩn hóa màn hình:**
   ```python
   def _attempt_detected_screen(attempt: dict[str, Any] | None) -> str:
       if not attempt:
           return ""
       return str(attempt.get("detected_screen") or attempt.get("detected") or "")
   ```
2. **Kiểm tra cả rỗng và "unknown" trước khi vào vòng lặp BACK:**
   ```python
   if _attempt_detected_screen(after) in ("", "unknown"):
       for back_i in range(1, 4):
           ...
           screen = _attempt_detected_screen(recovered)
           if screen in _KNOWN_TIKTOK_SCREENS_AFTER_ADD_PHONE:
               after = recovered
               break
           if screen and screen != "unknown":
               break
   ```
3. **Quy tắc:** Mọi điểm kiểm tra trạng thái màn hình để fallback hoặc recovery không bao giờ giả định classifier luôn trả về chuỗi `"unknown"` khi không nhận diện được; phải luôn guard cả trường hợp `None` và empty string `""`.
