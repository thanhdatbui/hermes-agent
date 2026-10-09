# Khắc phục lỗi "focused package unavailable" khi dumpsys window nghẽn buffer & Regex Samsung

## 1. Triệu chứng
Trong quá trình quan sát (`observe_current_screen`), script dừng với lỗi:
`manual review required: focused package unavailable` hoặc crash observe dù app TikTok vẫn hiển thị trên màn hình.

## 2. Nguyên nhân kỹ thuật
1. **Buffer bloat & Timeout trên Samsung Galaxy:**
   - Lệnh `dumpsys window` đầy đủ trên các dòng Samsung Galaxy (SM-G930F/W8 hoặc máy có Knox/Dual Messenger) trả về hàng trăm KB đến vài MB văn bản.
   - Khi chạy qua ADB shell, buffer bị nghẽn dẫn đến vượt ngưỡng timeout 5s, `result.ok` trả về `False` hoặc ADBError.
2. **Regex `FOCUS_RE` bỏ sót format Samsung:**
   - Dumpsys trên Samsung thường có dòng cửa sổ độc lập dạng:
     `Window{42a0b18 u0 com.ss.android.ugc.trill/com.ss.android.ugc.aweme.splash.SplashActivity}:`
     hoặc các trường `mFocusedWindow`, `mTopFullscreenOpaqueWindowState`.
   - Regex cũ bắt buộc phải có tiền tố `mCurrentFocus` / `mFocusedApp`, dẫn đến việc không bóc tách được package/activity.
3. **`safety_check` thiếu cơ chế cứu khi mất focus:**
   - Khi `focus_pkg` trả về `None`, nhưng UI XML đã dump được rõ ràng các thành phần TikTok (hoặc đã phân loại thành `is_known_tiktok_screen`), logic cũ vẫn văng lỗi `focused package unavailable`.

## 3. Giải pháp chuẩn đã triển khai

### `python_runner/flows/observe.py`
- **Đưa `dumpsys window displays` lên đầu:**
  ```python
  candidates = [
      ["dumpsys", "window", "displays"],  # Nhẹ (< 100ms), chứa đầy đủ current focus của display
      ["dumpsys", "window"],
      ["dumpsys", "activity", "activities"],
  ]
  ```
- **Fallback grep nhẹ trên thiết bị:**
  Chạy trực tiếp qua `sh -c` để Android grep trước khi đẩy qua ADB stream:
  ```python
  ctx.adb.shell(
      ["sh", "-c", "dumpsys window | grep -E 'mCurrentFocus|mFocusedApp|mFocusedWindow|mTopFullscreenOpaque'"],
      timeout=dumpsys_timeout,
  )
  ```
- **Mở rộng regex `FOCUS_RE`:**
  ```python
  FOCUS_RE = re.compile(
      r"(?:"
      r"(?:mCurrentFocus|mFocusedApp|topResumedActivity|mTopResumedActivity|mFocusedWindow|mTopFullscreenOpaqueWindowState|mTopFullscreenOpaqueWindow|mResumedActivity)"
      r"[^\n]*?(?:\s|^)"
      r"|Window\{[^\n}]*?\s"
      r")"
      r"([A-Za-z0-9_.]+)/(.[A-Za-z0-9_.$/]+|[A-Za-z0-9_.$/]+)"
  )
  ```

### `python_runner/core/safety.py`
- **Fallback cứu focus trong `safety_check`:**
  Nếu `focus_pkg is None` (hoặc overlay package), kiểm tra `is_known_tiktok_screen` hoặc `raw_xml` có chứa TikTok package/indicators (`is_tiktok_xml`):
  ```python
  has_xml_evidence = bool(xml_available or raw_xml)
  if (focus_pkg in SYSTEM_OVERLAY_PACKAGES or focus_pkg is None) and (
      is_known_tiktok_screen or (has_xml_evidence and is_tiktok_xml)
  ):
      logger.warning("Recovered focus_pkg to %s ...", expected)
      focus_pkg = expected
  ```
