# Avatar Upload: CDN Network Request Settle & Crop-Close Wait

## Root Cause
Trong luồng `ENSURE_AVATAR` (`D:\Taadaa\Tiktok-video\scripts\tiktok_workflow\state_machine.py`):
Khi bấm Lưu avatar trên màn crop, TikTok khởi tạo một network request bất đồng bộ (async) để tải ảnh avatar lên CDN của TikTok:
- Nếu code gọi `adapter.back()` hoặc ngay lập tức gọi `am force-stop` / đóng app, activity bị hủy và network request upload ngầm bị abort giữa chừng.
- Hậu quả: Avatar trên máy thật có vẻ đã đổi nhưng trên server TikTok (CDN) không được cập nhật, lần mở app sau hoặc máy khác nhìn vào avatar vẫn là ảnh cũ / mặc định.

## Contract & Fix Pattern

### 1. `_save_avatar_without_story`: Chờ màn crop đóng
Thay vì sleep cứng 4s rồi return ngay sau khi tap Save (`(792, 1794)` hoặc semantic/visual button), gọi `self._wait_for_avatar_crop_closed(adapter, timeout=15.0)`.
- Poll XML: kiểm tra xem UI đã quay về "Sửa hồ sơ" / "Profile root", hoặc các marker crop (`qii`, `rou`, `rts`, `sca`, `y75`, `zgs`, `zm1`, `"Lưu"`, `"Lưu và đăng"`, `"Cắt"`) đã biến mất.
- Poll Visual: chụp screenshot và kiểm tra `not self._is_avatar_save_surface_visual(visual)` (nút Save đỏ ở đáy màn hình không còn).

### 2. `_handle_ensure_avatar_impl`: Chờ upload hoàn tất & CDN settle
Sau khi `_save_avatar_without_story` hoàn thành:
- Gọi `self._wait_for_avatar_upload_complete(adapter, timeout=15.0)`:
  - Poll XML kiểm tra màn hình đã settle về "Sửa hồ sơ" / Profile (timeout 15s).
  - Sleep thêm ít nhất 8–10s (`avatar_upload_settle_sleep`, config overrideable, mặc định 8.0s) để request network CDN của TikTok gửi xong 100%.
- BỎ hoàn toàn `adapter.back()` sau save.
- Chụp artifact xác nhận `avatar-uploaded-confirmed.png`.
- Sau đó mới force-stop TikTok và đưa máy về Home:
  `adb.shell("am force-stop com.zhiliaoapp.musically; am force-stop com.ss.android.ugc.trill; input keyevent 3")`

## Unit-Testing Mock Pitfall: `lambda *a:` on `type('Adapter', ...)`
Khi tạo mock adapter bằng `type("Adapter", (), {"dump_ui": ...})()`:
- Nếu viết `"dump_ui": lambda: ...` (không nhận tham số), khi gọi qua instance `adapter.dump_ui()`, Python coi đó là instance method và tự động truyền `self` làm tham số đầu tiên -> ném `TypeError: <lambda>() takes 0 positional arguments but 1 was given`.
- Trong code có `try ... except Exception:` bọc quanh `adapter.dump_ui()`, exception này bị nuốt âm thầm khiến hàm wait tưởng XML luôn rỗng và trả về False.
- **Quy tắc:** Luôn viết `"dump_ui": lambda *a: ...` hoặc `"dump_ui": lambda self=None: ...` khi mock method trên class dict.
