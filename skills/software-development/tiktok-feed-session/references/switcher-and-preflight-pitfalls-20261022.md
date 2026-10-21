# TikTok Account Switcher & Preflight Pitfalls (2026-10-22)

## 1. M74 Anchor Misidentification: Display Name vs Username
- **Vấn đề:** M74 tap trúng username `@julesuqi6h4` thay vì mở switcher dropdown.
- **Root Cause:**
  - `_find_sticky_profile_header` kiểm tra `anchor.center[1] <= 320`. Display name `Anh Loan1` (`com.ss.android.ugc.trill:id/t_3`) có bounds `[36, 280][444, 364]` -> tâm `y = 322 > 320`, bị loại bỏ.
  - Flow ưu tiên `display_name_anchor_element` (FrameLayout rỗng) trước `display_name_element` thật.
- **Khắc phục:**
  - Ưu tiên `display_name_element` thật trước.
  - Sửa điều kiện thành `anchor.bounds is not None and anchor.bounds[1] <= 320`.

## 2. M78 Tap Trượt Danh Sách Account Full-Width
- **Vấn đề:** Switcher mở đúng nhưng tap vào dòng `anxinh858` không chuyển account, sau đó verify profile vẫn là nick cũ.
- **Root Cause:**
  - Row tài khoản `ls_` full màn hình `[0, y1][1080, y2]`.
  - Tap ở tâm `(540, center_y)` trúng khoảng trống giữa text và badge số thông báo `9+` (`p05`), không ăn click.
- **Khắc phục:**
  - Khi node bounds full width (`bounds[0] == 0` và `bounds[2] >= 1000`), tap vào mép trái `x = 350` (hoặc thu hẹp target về `min(b[0] + 600, b[2])`).

## 3. Khóa Kép khi Chạy Canary với `with_device_lock.py`
- **Vấn đề:** Wrapper `with_device_lock.py -m <N>` bọc ngoài `run_tiktok.py` khiến runner con bên trong gặp lỗi `skipped-device-locked` (do bị lock bởi chính wrapper).
- **Khắc phục:**
  - Sử dụng cờ `--no-lock` trên `with_device_lock.py` khi lệnh bên trong tự quản lý atomic `device_lock`.
