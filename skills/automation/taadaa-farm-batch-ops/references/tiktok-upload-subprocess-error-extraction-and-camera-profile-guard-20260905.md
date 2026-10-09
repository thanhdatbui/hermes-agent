# Quy chuẩn trích xuất lỗi Upload chi tiết và chống nhận nhầm Camera vs Profile (Case 82 & Case 83) — 2026-09-05

## 1. Hiện tượng & Phản hồi từ User
- **Phàn nàn của User:** "Sao cứ lỗi upload nonprocess zero... Lỗi gì thì ghi chính xác ra chứ"
- **Triệu chứng:** Khi tiến trình upload video (`run_post.py`) thất bại, Farm Alert trên Telegram luôn chỉ báo generic `Triệu chứng: upload_subprocess_nonzero`, không nêu được lỗi cụ thể (kẹt UI, timeout ADB, lệch tài khoản, kẹt mẫu CapCut, v.v.).

---

## 2. Nguyên nhân cốt lõi (Anti-Patterns)
1. **Hardcode fallback trong runner cha (`multi_machine_feed_session.py`):**
   - Tại hàm `_run_upload_hook`, khi tiến trình con `run_post.py` trả về exit code khác 0 (`proc.returncode != 0`), code cũ hardcode gán fallback `"reason": "upload_subprocess_nonzero"`.
   - Toàn bộ thông tin giá trị trong `report.json` (`error`, `reason`, `last_state`, `status`) và log lỗi chi tiết (`stderr`, `stdout`) bị vứt bỏ.
2. **Nguy cơ vỡ cú pháp HTML Telegram trong alert (`alerts.py`):**
   - Các biến động như `error_reason`, `account`, `serial`, `status_text` được chèn trực tiếp vào template HTML mà không qua `html.escape()`. Khi thông báo lỗi chứa ký tự đặc biệt như `<redacted>` (từ `SecretFilter`) hoặc `<module>`, Telegram API từ chối gửi (`can't parse entities`).
3. **Nhận nhầm Profile root là Camera surface (`state_machine.py` - Case 83):**
   - `_is_camera_surface_xml` kiểm tra các chuỗi `text="camera"`, `content-desc="camera"`, `text="đăng"`, `text="tạo"`.
   - Trên màn hình Profile root của TikTok, icon camera shortcut ở header có `content-desc="Camera"` và tab danh sách video có text `"Đăng"`.
   - Khi dismiss CapCut template hoặc back về Profile, `_is_camera_surface_xml` nhận nhầm Profile là Camera, kích hoạt hàm `_tap_visual_camera_upload_entry` tính tọa độ thumbnail góc dưới trái `(156, 1574)`.
   - Tọa độ này tap trúng video tile đầu tiên trên Profile grid -> mở Profile video playback surface (`sl0` / `view_entrance_text`), dẫn đến kẹt vòng lặp và dừng phiên với lỗi `[VIDEO_PICK_CREATE_ENTRY_UNCONFIRMED]`.

---

## 3. Quy chuẩn khắc phục (Standard Fixes)

### A. Bóc tách lỗi đa tầng trong `multi_machine_feed_session.py`
Sử dụng hàm helper chuẩn `_extract_upload_subprocess_error(rep_data, stderr, stdout, returncode)`:
1. **Tầng 1 (Report JSON):** Đọc từ `report.json` nếu có: `err = rep_data.get("error") or rep_data.get("reason")`. Kết hợp `[last_state] error` nếu có `last_state`.
2. **Tầng 2 (Stderr):** Nếu không có report, lấy dòng cuối không rỗng từ `stderr` (thường chứa Traceback / Exception).
3. **Tầng 3 (Stdout):** Quét ngược tìm dòng `[ERROR]`, `[CRITICAL]` hoặc `>>> State: <state>`.
4. **Tầng 4 (Fallback):** `upload_exit_code_{returncode}`.
5. Cắt ngắn tối đa 250 ký tự (`...`) để đảm bảo tin nhắn súc tích.

### B. Escape HTML an toàn trong `automation_core/alerts.py`
- Bắt buộc `import html`.
- Bọc `html.escape(str(...))` cho `error_reason`, `account`, `serial`, `status_text` trong `send_farm_machine_alert` và `send_farm_script_alert`.

### C. Triệt tiêu nhận nhầm Camera vs Profile (`state_machine.py` - Case 83)
Trong `_is_camera_surface_xml`:
1. **Loại trừ Profile playback surface:** `if cls._is_profile_video_playback_surface(xml_text): return False`.
2. **Loại trừ Profile root markers:** `sửa hồ sơ`, `chỉnh sửa hồ sơ`, `edit profile`, `chia sẻ hồ sơ`, `thêm tiểu sử`, `hoàn tất hồ sơ`, `:id/ny0`.
3. **Loại trừ Bottom Navigation Bar:** Nếu xuất hiện đồng thời cả `Trang chủ` và `Hồ sơ`, đây là màn hình tab chính, không phải Camera modal (Camera ẩn thanh đáy).
4. **Loại trừ Feed root:** `long_press_layout` kèm `dành cho bạn`, `for you`, `following`.
5. **Hàm phục hồi xem video cá nhân:** `_is_profile_video_playback_surface` (nhận diện `sl0`, `view_entrance_text`, `bq7`) + `_recover_profile_video_playback_surface` (tap `bq7` / `adapter.back()` để thoát ra Profile/Feed an toàn).

### D. Xử lý stale fingerprint reservation trước khi chạy lại Canary
Khi worker upload bị ngắt giữa chừng, file ledger reservation tại:
`D:\CodexRuntime\tiktok-video\idempotency\media-fingerprints\<hash>.json`
sẽ bị kẹt ở trạng thái `"status": "reserved"`. Trước khi chạy lệnh Canary đơn lẻ trên máy đó, bắt buộc tìm và xóa (unlink) file ledger reservation này để không bị chặn bởi `MEDIA_FINGERPRINT_PENDING`.
