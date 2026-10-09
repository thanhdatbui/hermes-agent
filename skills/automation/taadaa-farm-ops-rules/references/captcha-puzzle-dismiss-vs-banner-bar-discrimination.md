# Captcha Puzzle Dismiss vs Banner Bar Discrimination & False P0 Auth Classification

## 1. Sự cố kép tại ca Nuôi Acc / Lướt Feed (Máy 35)
- **Triệu chứng 1:** Cảnh báo `🚨 [BATCH ALERT: LỖI HỆ THỐNG] P0 CẢNH BÁO MẤT PHIÊN / VĂNG ACCOUNT` trên Máy 35 với lý do `manual_challenge marker detected`.
- **Triệu chứng 2:** Máy dính captcha giải đố dạng kéo mảnh ghép (`Xác minh để tiếp tục:`, `resource-id="captcha-verify-image"`), dù có nút đóng `X` ở góc trên bên phải nhưng script không bấm tắt mà dừng máy với trạng thái `manual-needed:manual_challenge`.

## 2. Nguyên nhân gốc rễ (2 tầng)

### Tầng 1: Báo động sai P0 trong `batch_aggregator.py`
- Runner gộp chung blocker type thành `login-gms-verification`.
- `batch_aggregator.py` ghép chuỗi `f"{m.error_type} {m.error_message}"` để so khớp `SESSION_LOST_KEYWORDS`.
- Vì `error_type` chứa chữ `login`, lỗi captcha/thử thách tạm thời (`manual_challenge`) bị bắt nhầm vào danh sách mất phiên thật (`session_lost_failures`).

### Tầng 2: Nút tắt Captcha bị loại trừ nhầm (`_find_captcha_puzzle_close_x`)
- Nút `X` tắt captcha của TikTok WebView mang `resource-id="verify-bar-close"` và bounds nhỏ gọn ở góc trên bên phải khung (ví dụ: `[867,559][972,664]`).
- Hàm `_find_captcha_puzzle_close_x` trong `automation-core` bị hardcode rule cũ: `exclude_resource_ids = ("verify-bar-close",)`.
- Rule này sinh ra từ thời xa xưa để tránh bấm vào thanh banner ngang trải dài toàn màn hình `[0,0][1080,120]`, nhưng vô tình triệt tiêu luôn nút `X` thật của TikTok captcha.

## 3. Quy chuẩn khắc phục chuẩn hóa (Invariant)

### A. Phân định ranh giới nút X thật vs Banner trong `_find_captcha_puzzle_close_x`:
- **Banner bar ngang:** `elem_w >= 0.5 * right_max` (chiếm từ nửa màn hình trở lên) -> **BẮT BUỘC LOẠI TRỪ (EXCLUDE)**.
- **Nút X thật góc trên bên phải:** Nằm trong vùng `in_top_right` (`cx >= 0.55 * right_max and cy <= 0.45 * bottom_max`) và có kích thước nhỏ gọn (`elem_w < 0.5 * right_max`) -> **CHO PHÉP BẤM TẮT (DISMISS_CLOSE_X)**.

```python
elem_w = element.bounds[2] - element.bounds[0]
if element.resource_id in exclude_resource_ids and elem_w >= 0.5 * right_max:
    continue
```

### B. Ưu tiên phân loại Challenge trước trong `batch_aggregator.py`:
- Luôn kiểm tra `CHALLENGE_KEYWORDS` trên `error_message` hoặc `error_type` thuần trước khi kiểm tra `SESSION_LOST_KEYWORDS`.
- Tránh để nhãn composite như `login-gms-verification` đè các lỗi captcha/xác minh thành P0 Mất phiên.
