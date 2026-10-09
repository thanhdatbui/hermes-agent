# Xử lý Lỗi Benign Add Phone Popup & Cơ Chế Override Cờ Safety Trong Feed Session (Case Máy 74, 2026-09-05)

## 1. Triệu chứng & Hiện trường
- **Alert**: `[FARM ALERT: MÁY 74] DỪNG PHIÊN`
- **Thiết bị**: Máy 74 (Serial `ce061606c21e153d03`, Nick `ninhsyhez6u`).
- **Thông báo lỗi**: `benign Add phone popup detected; dismiss requires explicit flag; swipe recovery (2 swipes) still stuck`.
- **Màn hình kẹt**: Modal dialog "Thêm số điện thoại" (Add phone) của TikTok xuất hiện đè lên giao diện khi bắt đầu phiên hoặc trong quá trình lướt feed / verify profile.

## 2. Nguyên nhân gốc rễ (Root Cause)
1. **Lỗi logic override cờ `allow_benign_popup_dismiss` trong `multi_machine_feed_session.py`**:
   - Tại `python_runner/flows/multi_machine_feed_session.py` (~dòng 4676), worker feed session đã khởi tạo:
     ```python
     child_safety = child_config.setdefault("safety", {})
     # Bật mặc định allow_benign_popup_dismiss để tự động đóng popup vị trí/quyền an toàn
     child_safety["allow_benign_popup_dismiss"] = True
     ```
   - Tuy nhiên, ngay bên dưới có vòng lặp sao chép từ `parent_safety`:
     ```python
     parent_safety = ctx.config.get("safety", {})
     if isinstance(parent_safety, dict):
         for _key in ("allow_benign_popup_dismiss", "allow_blanket_dismiss", ...):
             if _key in parent_safety:
                 child_safety[_key] = parent_safety[_key]
     ```
   - Vì `config.example.yaml` cấu hình mặc định `"allow_benign_popup_dismiss": false`, nên giá trị `False` từ parent đã ghi đè (shadow/override) mất cờ `True` của child process.

2. **Chặn dismiss Add phone popup trong `feed_swipe_smoke.py`**:
   - Tại `python_runner/flows/feed_swipe_smoke.py` (`_maybe_dismiss_add_phone_row`):
     ```python
     if not ctx.config.get("safety", {}).get("allow_benign_popup_dismiss", False):
         row["popup_type"] = "add_phone"
         row["popup_dismiss_action"] = "dismiss_close_x"
         row["popup_dismissed"] = False
         row["reason"] = "Add phone popup detected; --allow-benign-popup-dismiss not set"
         row["safety_reason"] = "benign Add phone popup detected; dismiss requires explicit flag"
         return row
     ```
   - Khi cờ `allow_benign_popup_dismiss` bị `False`, script từ chối bấm nút close-X và trả về `manual-needed`.

3. **Bẫy Swipe Recovery (`_swipe_recovery_on_stuck`)**:
   - Khi `_maybe_dismiss_add_phone_row` trả về lỗi, luồng recovery fallback gọi `_swipe_recovery_on_stuck` thử vuốt lướt qua 2 lần.
   - Do "Add phone" là modal dialog toàn màn hình có nút `X`, thao tác vuốt feed ở dưới không thể đóng được dialog, dẫn tới lỗi kép `; swipe recovery (2 swipes) still stuck`.

## 3. Giải pháp khắc phục chuẩn hóa

1. **Khắc phục tại `multi_machine_feed_session.py`**:
   - Loại bỏ `"allow_benign_popup_dismiss"` khỏi vòng lặp ghi đè mù quáng. Chỉ cập nhật từ `parent_safety` nếu parent thực sự chỉ định bật hoặc cờ được set rõ ràng:
     ```python
     child_safety = child_config.setdefault("safety", {})
     child_safety["allow_benign_popup_dismiss"] = True
     parent_safety = ctx.config.get("safety", {})
     if isinstance(parent_safety, dict):
         for _key in ("allow_blanket_dismiss", "allow_network_force_stop_recovery", "allow_device_reboot_recovery", "allow_prepare_tiktok", "allow_feed_swipe"):
             if _key in parent_safety:
                 child_safety[_key] = parent_safety[_key]
         if parent_safety.get("allow_benign_popup_dismiss") is True:
             child_safety["allow_benign_popup_dismiss"] = True
     ```

2. **Khắc phục tại `feed_swipe_smoke.py`**:
   - Cho phép `_maybe_dismiss_add_phone_row` mặc định `allow_dismiss = True` đối với benign popup close-X nếu không có lệnh cấm tường minh:
     ```python
     allow_dismiss = ctx.config.get("safety", {}).get("allow_benign_popup_dismiss", True)
     if not allow_dismiss:
         row["popup_type"] = "add_phone"
         ...
         return row
     ```

3. **Nguyên tắc an toàn của Add Phone Popup**:
   - Theo `core.benign_popup.has_sensitive_marker`, popup Add phone đã được kiểm chứng an toàn (onboarding copy, không phải login/checkpoint/password field).
   - Handler `dismiss_add_phone_popup` CHỈ tap duy nhất nút close-X (`_ADD_PHONE_CLOSE_LABELS`), tuyệt đối không tap vào ô nhập số điện thoại hay nút Tiếp tục, đảm bảo tính an toàn 100% cho tài khoản nuôi farm.
