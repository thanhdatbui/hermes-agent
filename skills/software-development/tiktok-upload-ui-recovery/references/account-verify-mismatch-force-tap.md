# Case: ACCOUNT_VERIFY_MISMATCH do tap_profile() bỏ qua duplicate tap khi retry

## Bối cảnh & Triệu chứng
- **Triệu chứng:** Khi chạy `Tiktok-video` đăng video hoặc switch account, run fail tại state `ACCOUNT_READY` với lỗi:
  `[ACCOUNT_SWITCHER_FAILED] ACCOUNT_READY verify failed: ACCOUNT_VERIFY_MISMATCH: Profile did not show the expected account`
- **Log đặc trưng:**
  ```text
  [WARNING] scripts.tiktok_workflow.state_machine: [ACCOUNT_READY] Profile account verify pending: ACCOUNT_VERIFY_MISMATCH: Profile did not show the expected account; re-tapping Profile tab...
  [INFO] scripts.tiktok_workflow.adapter: [TAP_PROFILE] Profile root already visible; skip duplicate tap
  [WARNING] scripts.tiktok_workflow.state_machine: [ACCOUNT_READY] Profile account verify pending: ...
  [INFO] scripts.tiktok_workflow.adapter: [TAP_PROFILE] Profile root already visible; skip duplicate tap
  ```

## Nguyên nhân gốc rễ
1. Trong `scripts/tiktok_workflow/adapter.py`, hàm `tap_profile()` có kiểm tra:
   ```python
   if self.is_profile_root(xml_text):
       logger.info("[TAP_PROFILE] Profile root already visible; skip duplicate tap")
       return
   ```
2. Khi tài khoản vừa được chọn trong Account Switcher, giao diện có thể vẫn đang hiển thị profile của nick cũ (hoặc đang load dở, hoặc ở feed nhưng `is_profile_root` bị true do banner/layout).
3. Khi `_handle_account_ready` phát hiện account mismatch và gọi `tap_profile()` để re-navigate/refresh tab Profile, `tap_profile()` thấy `is_profile_root(xml_text)` là True nên huỷ bỏ lệnh tap thật xuống máy.
4. Hậu quả: Toàn bộ các lần retry trong deadline 20s đều bị bỏ qua (no-op), dẫn đến `ACCOUNT_VERIFY_MISMATCH` và đẩy workflow sang `MANUAL_REVIEW`.

## Giải pháp chuẩn hóa (Fix Pattern)
1. **Thêm `force: bool = False` cho `tap_profile` trong `adapter.py`:**
   ```python
   def tap_profile(self, force: bool = False) -> None:
       # ...
       if not force and self.is_profile_root(xml_text):
           logger.info("[TAP_PROFILE] Profile root already visible; skip duplicate tap")
           return
   ```
2. **Ép `force=True` khi retry verify account trong `state_machine.py`:**
   ```python
   except Exception as exc:
       logger.warning("[ACCOUNT_READY] Profile account verify pending: %s; re-tapping Profile tab...", exc)
       try:
           self.context.adapter.tap_profile(force=True)
       except TypeError:
           self.context.adapter.tap_profile()
       time.sleep(2.5)
   ```
3. Việc tap lại tab Hồ sơ trên TikTok khi đang ở Hồ sơ sẽ kích hoạt cơ chế scroll-to-top và refresh profile của TikTok, giúp load đúng profile mới của tài khoản mục tiêu.
