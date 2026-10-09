# Focused Package Unavailable: Floating Widget & Code Search Prune (2026-09-06)

## 1. Triệu chứng & Bối cảnh (Máy 42 - Nick allisononels67)
- **Lỗi**: `focused package unavailable` (hoặc `package unavailable`).
- **Hiện trường**: App TikTok đang mở bình thường ở tab Đề xuất (Home feed), nhưng trên màn hình có widget nổi/floating floater (ví dụ: *"Nhấp ngay có thưởng"*, campaign widget góc trên trái, bong bóng thông báo).
- **Hậu quả**: Phiên chạy bị ngắt `SAFETY_FAILED`, giữ hiện trường oan uổng dù người dùng thấy TikTok vẫn đang mở ngay trước mắt.

## 2. Root Cause Analysis

### A. `observe.py: get_focused_activity` bị che khuất bởi floating window
- Khi có widget nổi, `dumpsys window | grep -E "mCurrentFocus|mFocusedApp"` có thể trả về window của sub-layer, window null, hoặc trạng thái animation không chứa package chính.
- `parse_focused_activity` không bóc tách được package, trả về `{"package": None, "activity": None}`.

### B. `safety.py: safety_check` điều kiện giải cứu quá hẹp
- Đoạn mã trong `core/safety.py`:
  ```python
  is_known_tiktok_screen = (
      detected in KNOWN_TIKTOK_SCREENS
      or detected in MANUAL_SCREEN_REASONS
  )
  if (focus_pkg in SYSTEM_OVERLAY_PACKAGES or focus_pkg is None) and xml_available and is_known_tiktok_screen:
      focus_pkg = expected
  elif focus_pkg is None:
      return SafetyCheckResult(
          SAFETY_FAILED,
          "focused package unavailable",
          ...
      )
  ```
- **Lỗ hổng**: Chỉ giải cứu `focus_pkg = expected` khi `is_known_tiktok_screen` là True (`detected` phải nằm trong tập cứng `{"home", "friends", "following", "for-you", "profile"}`).
- Khi có floating widget ("Nhấp ngay có thưởng"), hàm phát hiện màn hình (`detect_screen`) có thể trả về `None`, chuỗi popup chưa gán nhãn, hoặc màn hình không khớp chính xác 5 nhãn trên. Khi đó, dù `xml_available` là True và XML chứa đầy các thuộc tính của `com.zhiliaoapp.musically` / `com.ss.android.ugc.trill`, nhánh giải cứu bị bỏ qua và rơi thẳng vào `elif focus_pkg is None: return SafetyCheckResult(SAFETY_FAILED, "focused package unavailable")`.

## 3. Quy chuẩn Sửa chữa & Fallback (Resolution Pattern)

1. **Fallback cấp độ trích xuất focus (`observe.py: get_focused_activity`)**:
   - Khi `mCurrentFocus` / `mFocusedApp` trả về `None`:
     - Thử fallback qua `dumpsys activity recents | grep -E "Recent #0"` hoặc `dumpsys window windows | grep "mHasSurface=true" | grep -E "(com.zhiliaoapp.musically|com.ss.android.ugc.trill)"`.
     - Hoặc kiểm tra nhanh UI XML hierarchy nếu đã dump được, kiểm tra sự hiện diện của `package="com.zhiliaoapp.musically"` hoặc `package="com.ss.android.ugc.trill"`.

2. **Gia cố `core/safety.py: safety_check`**:
   - Mở rộng điều kiện giải cứu: nếu `focus_pkg is None` và `xml_available is True`, kiểm tra xem XML hoặc detector có dấu hiệu của TikTok hay không (không bắt buộc `detected` phải nằm cứng trong 5 nhãn cũ nếu XML khẳng định rõ ràng là app TikTok đang foreground).

## 4. Pitfall cốt tử khi debug: Cấm quét đĩa / Bắt buộc prune thư mục log
- **Hiện tượng**: Gọi `find`, `grep -rn`, `os.walk` hoặc `search_files` trong `D:\Taadaa\tiktok-luot nuoi acc` hoặc `python_runner` bị **TIMED OUT 900s**, trigger tool loop warning.
- **Nguyên nhân**: Cả thư mục gốc repo VÀ thư mục `python_runner` đều chứa `.ai-runs` và `runs` với hàng trăm run directories và hàng trăm ngàn artifacts.
- **Quy tắc bắt buộc**:
  - Dùng `python D:/Taadaa/tools/inspect_machine.py <N>` để lấy log hiện trường của máy.
  - Nếu bắt buộc phải dùng script Python rà soát code trong `python_runner`, **BẮT BUỘC** loại trừ các thư mục lớn:
    ```python
    exclude = {".ai-runs", "runs", ".git", ".pytest_cache", "__pycache__"}
    for root, dirs, files in os.walk(runner_dir):
        dirs[:] = [d for d in dirs if d not in exclude]
        ...
    ```
