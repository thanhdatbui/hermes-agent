# Popup Dismiss Recapture Guard & Camera Creation Marker Precision (2026-08-26)

## 1. Lỗi 'NoneType' object has no attribute 'get' khi xử lý Popup Dismiss

### Triệu chứng & Nguyên nhân
- Trong `feed_swipe_smoke.py`, khi gọi dismiss popup qua `_dismiss_allowed_or_blanket_popup` hoặc các handler tương đương, một số handler có thể trả về `PopupDismissResult(dismissed=True, ...)` nhưng `after_attempt=None` (hoặc `after_attempt` chưa được recapture thành công).
- Code luồng xử lý trước đây chỉ kiểm tra `if not dismiss.dismissed: ...` rồi mặc định truy cập `dismiss.after_attempt.get(...)` ở các dòng tiếp theo, dẫn đến crash runtime `AttributeError: 'NoneType' object has no attribute 'get'`.

### Quy tắc xử lý chuẩn (Fail-closed & Safe Dereference)
Bắt buộc kiểm tra cả `dismiss.dismissed` và `dismiss.after_attempt is None`:
```python
if not dismiss.dismissed or dismiss.after_attempt is None:
    if dismiss.dismissed:
        # A dismiss result is only usable after a verified recapture.
        row["popup_dismissed"] = False
        row["reason"] = "popup dismiss reported success but recapture was unavailable"
        row["safety_reason"] = row["reason"]
        return row
    ...
```

---

## 2. Tránh False-Positive Camera Creation Overlay trên trang Profile

### Triệu chứng
- Khi verify profile (`_verify_profile_after_session`), hệ thống liên tục báo `dismiss_camera_creation_overlay_before_verify` và sau đó báo `profile verification mismatch: profile account mismatch`, mặc dù màn hình thực tế đã ở đúng tab Hồ sơ.

### Nguyên nhân
- `_detect_camera_creation` trong `benign_popup_registry.py` chứa các từ quá chung chung: `["ĐĂNG", "TẠO"]`.
- Trên giao diện Profile bình thường của TikTok tiếng Việt luôn xuất hiện các cụm từ như `"Tạo một Nhật ký"`, `"Bài đăng"`, `"Ảnh hồ sơ"`. Khi cộng dồn match count >= 2, hàm nhận diện nhầm trang Profile là màn hình Camera/Creation Overlay, kích hoạt flow dismiss camera (bấm BACK và re-tap Profile), làm gián đoạn đối soát username.

### Quy tắc chọn Marker Camera Creation
- Loại bỏ các từ đơn generic như `ĐĂNG`, `TẠO`.
- Chỉ giữ các marker đặc trưng của chế độ quay/chụp:
  `["10 phút", "60s", "15s", "ẢNH", "VĂN BẢN", "10m", "Photo", "Templates", "CAMERA"]`.
