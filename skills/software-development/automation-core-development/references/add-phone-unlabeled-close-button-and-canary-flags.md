# Add Phone Unlabeled Close Button Fix & Canary Protocol

## 1. False-Positive P0 "login/account screen detected" trên Bottom Sheet "Thêm số điện thoại"

### Hiện tượng:
- Alert batch báo lỗi P0: `[P0 CẢNH BÁO MẤT PHIÊN / VĂNG ACCOUNT]: Máy MN: login/account screen detected`.
- Kiểm tra XML/screenshot hiện trường phát hiện tài khoản KHÔNG hề bị logout hay văng phiên.
- Màn hình thực tế là bottom sheet **"Thêm số điện thoại"** (`Trang tính dưới cùng`):
  - Nội dung mô tả: *"Thêm số điện thoại của bạn để tăng cường bảo mật, khôi phục tài khoản dễ hơn và đăng nhập nhanh hơn."*
  - Ô nhập `EditText` số điện thoại: `bounds=[469,663][918,723]`.
  - Nút đóng (X) tại góc trên bên phải: `bounds=[936,84][1056,216]`, class `android.widget.Button` hoặc `ImageView`, nhưng `text=""` và `content-desc=""` (unlabeled).

### Nguyên nhân gốc rễ (Root Cause):
1. `_close_candidate(elements)` trong `automation_core/tiktok/benign_popup.py` trước đây chỉ đối soát label với `_ADD_PHONE_CLOSE_LABELS` (`"Đóng"`, `"Close"`, `"X"`). Với nút icon đóng không có nhãn chữ, hàm trả về `None`.
2. Do không tìm thấy nút đóng, `detect_add_phone_popup()` thất bại (`None`).
3. Bộ phân loại `classifier.py` rơi xuống fallback `has_sensitive_marker(root)`.
4. `has_sensitive_marker` phát hiện từ khóa `"tài khoản"`, `"đăng nhập"` trong đoạn text mô tả kết hợp với ô nhập `EditText` -> gán nhầm thành `manual-needed:login` ("login/account screen detected").

### Giải pháp kỹ thuật (Fix Pattern):
Trong `automation_core/tiktok/benign_popup.py` (`_close_candidate`):
- Bổ sung nhóm `unlabeled_candidates` thu thập UIElement không có text/content-desc nhưng thoả mãn:
  - Tọa độ góc trên bên phải: `left >= 800`, `top <= 350`.
  - Loại trừ nút hành động tiếp tục (`"tiếp tục"`, `"continue"`).
  - Thuộc tính tương tác: `element.attrib.get("clickable") == "true"` hoặc class chứa `"button"` / `"image"`.
- Thứ tự ưu tiên: `pool = candidates or unlabeled_candidates`.
- Nhờ vậy, `detect_add_phone_popup()` nhận diện thành công nút đóng không nhãn, trả về selector tọa độ `center=(996, 150)` để flow `dismiss_close_x` tự động bấm tắt.

---

## 2. Quy tắc chạy Canary Test đơn máy sau khi sửa flow Feed Session

### Lệnh chạy chuẩn:
```bash
python "D:/Taadaa/tiktok-luot nuoi acc/python_runner/run_tiktok.py" \
  --mode feed-session-smoke \
  --device <SERIAL> \
  --machine <N> \
  --account "<ACTIVE_USERNAME>" \
  --account-slot <SLOT> \
  --allow-navigation-only \
  --allow-feed-swipe \
  --allow-benign-popup-dismiss \
  --max-swipes 2 \
  --artifact-root "D:/Taadaa/runtime/kibe/canary_m<N>"
```

### Các cạm bẫy bắt buộc nhớ (Pitfalls):
1. **CẤM truyền `--prepare-tiktok` trong single-device `feed-session-smoke`:** Flag này bị chặn ở validator config và chỉ hỗ trợ cho `run-plan-smoke`, `multi-machine-smoke`, và `multi-machine-feed-session`.
2. **BẮT BUỘC có `--allow-navigation-only`:** `feed-session-smoke` yêu cầu navigation taps để chuyển tab Home/Profile. Nếu thiếu sẽ bị từ chối ngay lập tức (`feed-session-smoke requires --allow-navigation-only`).
3. **`--account` phải đúng nick đang active trên máy:** Nếu máy đang ở slot 1 (`@hongggg.yn`) mà truyền account của slot 7 (`lolahjdzo15`), flow vẫn lướt feed thành công nhưng bước `verify_profile` cuối cùng sẽ báo lỗi `profile verification mismatch: profile account mismatch`. Luôn kiểm tra nick active qua slot mapping hoặc XML trước khi chạy.
4. **Quy tắc Capture-Before-Cleanup:** Luôn kiểm tra screenshot nghiệm thu (`swipe_2_after/attempt_1/screen.png` và `verify_profile/screen.png`) trong thư mục artifact trước khi chạy lệnh teardown (`am force-stop`, `input keyevent 3`, `screen_off_timeout 600000`, `svc power stayon false`).
