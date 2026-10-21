# Canary Verification & Switcher Occlusion Recipes (2026-10-21)

## 1. Canary Gate Bắt Buộc Sau Khi Fix Lỗi (Anti-Skipping Gate)
- **Quy tắc cứng:** Sửa code (kể cả O(1) surgery) **KHÔNG ĐƯỢC DỪNG LẠI Ở UNIT TEST HAY DRY-RUN**. Sửa xong bắt buộc kích hoạt ngay Canary Gate chạy test 1 lượt trên đúng 1 máy thật đại diện (ví dụ máy bị lỗi trước đó) dưới `with_device_lock.py`.
- **Lệnh chạy Canary mẫu trên 1 máy thật:**
  ```bash
  python D:/Taadaa/tools/with_device_lock.py -m <N> -- env -u PYTHONPATH "D:/Taadaa/python-envs/automation/Scripts/python.exe" "D:/Taadaa/tiktok-luot nuoi acc/python_runner/run_tiktok.py" --machine <N> --account-workbook "D:/OneDrive/TaadaaData/kibe/taikhoan_run_safe.xlsx" --account-row-index <ROW> --mode multi-machine-feed-session --machines <N> --allow-navigation-only --allow-feed-swipe --allow-benign-popup-dismiss --verify-current-account --recovery-test-swipes 1 --config "D:/Taadaa/tiktok-luot nuoi acc/config.example.yaml"
  ```
- **Lưu ý thực thi:**
  - Bắt buộc chạy nền qua `terminal(background=True, notify_on_complete=True)`.
  - Phải có `env -u PYTHONPATH` để tránh python venv của hermes-agent gây đụng độ `_imaging` (PIL).
  - Khi hoàn thành, BẮT BUỘC soi mắt artifact ảnh bằng WinRT OCR hoặc `browser_vision` theo Gate 6 trước khi kết luận.

---

## 2. Các Lỗi Profile Switcher & Occlusion Đã Đúc Kết
1. **Lệch tâm Display Name (Bài học M74):**
   - Node display name `t_3` có bounds `[36, 280][444, 364]` -> tâm y = 322px.
   - Nếu so sánh `anchor.center[1] <= 320` sẽ loại bỏ node display name và rơi xuống nút copy username `@handle` (`t6f` ở y=392).
   - **Giải pháp:** Kiểm tra mép trên `anchor.bounds[1] <= 320` và ưu tiên node `display_name_element` thật trước.

2. **Account Switcher Tap trượt hàng Full-Width (Bài học M78):**
   - Hàng tài khoản dạng RecyclerView có bounds full ngang `[0, 1572][1080, 1788]`.
   - Tap vào tâm `(540, 1680)` rơi trúng khoảng trống giữa tên tài khoản và badge `9+` bên phải, không kích hoạt event chuyển nick.
   - **Giải pháp:** Căn chỉnh tọa độ tap vào mép trái (`x = 350`) để trúng vùng avatar / text của tài khoản.

3. **Occlusion Samsung FOTA Update (Bài học M261):**
   - Gói `com.wssyncmldm` hiển thị popup cập nhật phần mềm đè màn hình TikTok.
   - **Giải pháp:** Thêm `com.wssyncmldm` vào `SYSTEM_OCCLUSION_PACKAGES` để `recover_systemui_occlusion` gửi phím BACK (keyevent 4) giải phóng focus cho TikTok.
