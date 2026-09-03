# Account Switcher Sticky Header Bounds, BACK-Drift Recovery & Registry Recapture Contract

## 1. Profile Sticky Header Bounds Check (`_find_sticky_profile_header`)
- **Vấn đề**: Trên TikTok v46+, phần tử display name ở thân trang hồ sơ (unscrolled profile body, `center_y > 400px`) có thuộc tính `clickable="true"`, nhưng khi tap vào lại không bung Account Switcher (chỉ có sticky header ở đỉnh màn hình hoặc top bar mới mở được).
- **Quy tắc**:
  - `_find_sticky_profile_header` bắt buộc phải kiểm tra tọa độ `center[1] <= 320` (vùng header đỉnh màn hình).
  - Nếu profile chưa cuộn và display name nằm ở thân trang (`center[1] > 320`), hàm phải trả về `None` để flow gọi `_profile_scroll` (cuộn nhẹ lên ~400px) đưa sticky header (`com.ss.android.ugc.trill:id/pcq` hoặc tương đương) lên giữa đỉnh trước khi tap mở switcher.

## 2. Xử lý Drift khi nhấn phím BACK trong Recovery (`_capture_profile_switcher_xml_with_add_phone_guard`)
- **Vấn đề**: Khi tap vào anchor nhưng switcher không mở (hoặc kẹt overlay), nếu recovery bấm phím `BACK` (`keyevent 4`) khi đang ở Profile root mà không có overlay, TikTok sẽ lùi về tab trước đó (Bạn bè / Dành cho bạn / Khám phá).
- **Quy tắc**:
  - Sau khi gửi BACK, bắt buộc kiểm tra xem màn hình hiện tại có bị văng khỏi Profile root hay không (`_selected_bottom_tab` hoặc `_is_profile_root`).
  - Nếu đã bị drift về Feed/Home: Gọi `_navigate_profile_for_preflight` để quay lại tab Hồ sơ.
  - Khi đã ở lại Profile root: Thực hiện `_profile_scroll` để kích hoạt sticky header, capture fresh XML, resolve lại anchor mới rồi mới tap lại (`re_tap_profile_switch_anchor`).

## 3. Contract Bắt buộc Recapture sau khi Registry Dismiss Popup
- **Vấn đề**: Khi `benign_popup_registry.py` xử lý đóng popup thành công (`dismissed=True`) nhưng trả về `after_attempt=None`, flow kiểm tra `if not dismiss.dismissed or dismiss.after_attempt is None:` sẽ báo lỗi `popup dismiss reported success but recapture was unavailable`.
- **Quy tắc**:
  - Dispatcher trong `flows/benign_popup.py` khi nhận kết quả `dismissed=True` từ registry mà thiếu `after_attempt` phải tự động gọi `capture_calibration_attempt(ctx, f"{matching_entry.name}_dismiss", 1, focus=focus)` để bổ sung verified `after_attempt`.

## 4. Cô lập PYTHONPATH trong Launcher Scripts (`run-feed-session.ps1`)
- **Vấn đề**: Khi PowerShell launcher kế thừa `PYTHONPATH` từ môi trường ngoài (ví dụ agent venv khác phiên bản Python), tiến trình automation runner bị xung đột binary thư viện (ví dụ `ImportError: cannot import name '_imaging' from 'PIL'`).
- **Quy tắc**:
  - Trong launcher PowerShell/Bash, luôn set tường minh `$env:PYTHONPATH = "$projectRoot\python_runner;D:\Taadaa\automation-core\src"` trước khi invoke `python.exe`.
