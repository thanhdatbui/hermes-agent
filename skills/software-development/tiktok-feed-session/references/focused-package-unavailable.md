# Sự cố 'focused package unavailable' & Cơ chế Fallback Dumpsys Focus

## 1. Hiện tượng & Triệu chứng
- Alert báo: `focused package unavailable` trong quy trình Nuôi Acc / Lướt Feed (`feed_swipe_smoke.py`).
- Màn hình thực tế của máy vẫn đang mở TikTok ở Feed/Đề xuất hoặc profile bình thường, nhưng script bị dừng với `SAFETY_FAILED: focused package unavailable`.

## 2. Nguyên nhân gốc rễ (Root Cause)
Hàm `get_focused_activity(ctx)` trong `flows/observe.py` hoạt động theo 2 tầng:
1. **Tầng 1 (ATX-Primary):** Gọi `capture_atx_session_ui(ctx.adb, timeout=3.0)`. Nếu tiến trình `atx-agent` bị kẹt (ví dụ trạng thái `futex_wait_queue_me`), uiautomator daemon bị crash/treo, lệnh này quá timeout 3.0s và nhảy vào khối `except: pass`.
2. **Tầng 2 (Dumpsys Fallback):** Script fallback sang:
   ```python
   candidates = [
       ["dumpsys", "window"],
       ["dumpsys", "activity", "activities"],
   ]
   dumpsys_timeout = min(5.0, float(ctx.timeout("adb_seconds", 15)))
   ```
   **Điểm nghẽn:** `dumpsys window` đầy đủ trên các dòng máy Android/Samsung trả về dữ liệu rất lớn (hàng chục nghìn dòng log, 1–5MB qua ADB shell stream). Với timeout 5s, ADB stream bị nghẽn buffer hoặc time out trước khi truyền xong. Kết quả: `get_focused_activity` trả về `{'package': None, 'activity': None}`.
3. **Tầng 3 (Safety Check):** Tại `core/safety.py:safety_check()`, khi `focus_pkg is None`, nếu không nhận diện được XML màn hình là TikTok hợp lệ, hệ thống ném `SAFETY_FAILED: focused package unavailable`.

## 3. Quy tắc Fix & Code Pattern chuẩn

### A. Tối ưu lệnh Dumpsys trong `flows/observe.py`
Không gọi full `dumpsys window`. Ưu tiên lệnh trúng đích, nhẹ (dưới 100 dòng), trả về trong < 500ms:
- `dumpsys window displays` (rất nhẹ, chứa `mCurrentFocus` / `mFocusedApp`).
- Dùng shell pipe lọc trực tiếp trên device:
  ```python
  fast_focus = ctx.adb.shell(
      ["sh", "-c", "dumpsys window | grep -E 'mCurrentFocus|mFocusedApp|mFocusedWindow'"],
      timeout=3.0
  )
  ```
- Thêm regex khớp linh hoạt cả định dạng `Window{... package/activity}`:
  ```python
  FOCUS_RE = re.compile(
      r"(?:mCurrentFocus|mFocusedApp|topResumedActivity|mTopResumedActivity|mFocusedWindow|mTopFullscreenOpaqueWindowState|mResumedActivity)"
      r"[^\n]*?(?:[\s{]|^)([A-Za-z0-9_.]+)/(.[A-Za-z0-9_.$/]+|[A-Za-z0-9_.$/]+)"
  )
  ```

### B. Fallback an toàn trong `core/safety.py`
Khi `focus_pkg is None`:
- Nếu XML dump hoặc uiautomator chứa các node có package TikTok (`com.ss.android.ugc.trill`, `com.zhiliaoapp.musically`, `com.ss.android.ugc.aweme`), coi như TikTok vẫn đang active thay vì fail sớm với `focused package unavailable`.

## 4. Cảnh báo điều tra (Anti-minefield)
- **CẤM GREP TOÀN BỘ THƯ MỤC `.ai-runs`:** Thư mục `.ai-runs` chứa hàng trăm session lịch sử và hàng triệu dòng log. Lệnh `grep -rn` quét qua `.ai-runs` sẽ bị timeout (quá 900s).
- Khi điều tra lỗi focus, kiểm tra trực tiếp code tại `flows/observe.py` và `core/safety.py`.
