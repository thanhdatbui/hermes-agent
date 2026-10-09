# Switcher Prepare Loop, Suffix pq2, S7 Splash Token Ghosting & SECURITY_NOT_REACHED Triage (2026-09-08)

## 1. Bẫy Vòng Lặp Vô Hạn `prepare_switcher_anchor()` trong `open_switcher()`
- **Vị trí:** `automation-core/src/automation_core/tiktok/account_switcher.py`, hàm `open_switcher()`.
- **Cơ chế lỗi:**
  ```python
  # Code cũ:
  if anchor is None:
      prepare = getattr(adapter, "prepare_switcher_anchor", None)
      if callable(prepare):
          if prepare() is not False:
              continue
  ```
  `_CanonicalAdapter.prepare_switcher_anchor()` (trong `account_preflight.py`) thực hiện swipe nhẹ sticky header và LUÔN trả về `True`.
  Với `attempts=2`:
  - Attempt 0: `anchor is None` -> gọi `prepare()` -> trả về `True` -> `continue`.
  - Attempt 1: `anchor` vẫn `None` (do thiếu suffix hoặc text không bắt đầu bằng `@`) -> tiếp tục gọi `prepare()` -> trả về `True` -> `continue`.
  - Kết thúc vòng lặp `for attempt in range(max_attempts)` mà **KHÔNG BAO GIỜ** rơi xuống nhánh fallback tap `(screen_width // 2, screen_height * 150/1920)` phía dưới!
  - Cuối hàm raise thẳng: `AccountSwitcherError("SWITCHER_OPEN_FAILED", "could not open account switcher")`.
- **Bản vá chuẩn:**
  ```python
  if anchor is None and attempt == 0:
      prepare = getattr(adapter, "prepare_switcher_anchor", None)
      if callable(prepare):
          if prepare() is not False:
              continue
  ```
  Chỉ swipe prepare ở attempt 0. Nếu sang attempt 1 vẫn không phân giải được anchor semantic/resource thì BẮT BUỘC cho rơi xuống nhánh viewport fallback tap.

---

## 2. Resource ID Suffix Mới: `pq2` trên Sticky Header
- **Hiện trường máy 40:** UI TikTok khi cuộn nhẹ (sticky header) hiển thị tên tài khoản trong node:
  - `resource-id`: `com.ss.android.ugc.trill:id/pq2`
  - `bounds`: `[366, 72][720, 228]` (center: `x=543, y=150`)
  - `text`: `nguyenkhoi1403` (không có tiền tố `@`!)
- **Khắc phục:** Bổ sung `"pq2"` vào `_SWITCH_ANCHOR_RESOURCE_SUFFIXES` trong `account_switcher.py` và cập nhật test suite `tests/test_account_switcher_preconfirmed.py`.

---

## 3. Samsung S7 Android 7: Hiện Tượng WindowManager Ghosting Token `SplashActivity`
- **Triệu chứng:**
  - Chạy `dumpsys window | grep -E 'mCurrentFocus|mFocusedApp'` trả về:
    `com.ss.android.ugc.trill/com.ss.android.ugc.aweme.splash.SplashActivity`
  - Khiến agent hoặc script phán đoán sai lầm rằng *"TikTok đang bị treo/kẹt ở màn hình khởi động SplashActivity"*.
- **Thực tế:**
  - Trên Samsung S7 (Android 7.0), WindowManager giữ window token của `SplashActivity` ở cấp OS, nhưng view hierarchy bên trong đã chuyển sang `MainActivity` và render hoàn chỉnh trang Profile (`com.ss.android.ugc.trill:id/ok0` selected).
  - Dump UI qua ATX session (`dumpWindowHierarchy`) hoặc screencap cho thấy màn hình Profile đã sẵn sàng.
- **Kỷ luật:** CẤM chỉ nhìn vào `mCurrentFocus=SplashActivity` để kết luận TikTok treo. Bắt buộc kiểm tra kết hợp giữa XML dump thực tế và ảnh chụp màn hình (screencap).

---

## 4. Lỗi `SECURITY_NOT_REACHED` do Tiêu Đề Rút Gọn Màn Hình Cài Đặt
- **Vị trí:** `python_runner/core/f2a_classifier.py` và `python_runner/core/live_phase_b_adapter.py`.
- **Nguyên nhân:**
  1. Trong `f2a_classifier.py`, `F2AScreen.SECURITY` chỉ được phân loại khi có đúng chuỗi `"bảo mật & quyền"` hoặc `"bảo mật và quyền"`. Trên nhiều phiên bản TikTok mới hoặc giao diện rút gọn, màn hình Bảo mật chỉ có tiêu đề `"Bảo mật"` (hoặc tiếng Anh `"Security"` / `"Security and permissions"`) đi kèm các mục con `"Xác minh 2 bước"`, `"Cảnh báo bảo mật"`, `"Quản lý thiết bị"`. Do thiếu các marker này, màn hình bị gán nhãn `UNKNOWN` và timeout 60s dẫn tới `SECURITY_NOT_REACHED`.
  2. Trong `live_phase_b_adapter.py` dòng 481, lệnh tap gọi cứng `self._tap_value("Bảo mật & quyền")` thiếu fallback cho nhãn `"Bảo mật"` rút gọn.
- **Bản vá chuẩn:**
  1. Mở rộng `f2a_classifier.py`:
     ```python
     if _has(text_values, "bảo mật & quyền", "bảo mật và quyền", "security and permissions", "security & permissions") or (
         _has(text_values, "bảo mật", "security") and _has(text_values, "xác minh 2 bước", "2-step verification", "cảnh báo bảo mật", "quản lý thiết bị", "manage devices")
     ):
         if _has(text_values, "xác minh 2 bước", "2-step verification"):
             markers.append("text:xác minh 2 bước")
         markers.append("text:bảo mật")
         return Classification(F2AScreen.SECURITY, "high", tuple(markers))
     ```
  2. Thêm fallback trong `live_phase_b_adapter.py`:
     ```python
     try:
         self._tap_value("Bảo mật & quyền", prefix=True)
     except LiveAdapterError:
         self._tap_value("Bảo mật", prefix=True)
     self._wait_for(lambda xml: classify(xml).screen == F2AScreen.SECURITY, "SECURITY_NOT_REACHED")
     ```
  3. Bổ sung `"Bảo mật": "Security"` vào `_BILINGUAL_LABELS`.
