# Pitfalls & Rules: Profile Switcher Anchor, Occlusion & Canary Double Lock (2026-10-22)

## 1. Anchor Display Name vs Username Tap Target
- **Hiện tượng:** Máy nhận diện sai anchor Profile Header hoặc bấm nhầm vào text username (@handle) gây copy clipboard thay vì mở Switcher dropdown (ví dụ M74).
- **Nguyên nhân:**
  - `_find_sticky_profile_header` kiểm tra `anchor.center[1] <= 320`. Tuy nhiên trên nhiều máy S7/Android, display name `t_3` nằm ở bounds `[36, 280][444, 364]` -> tâm `y = 322 > 320`, dẫn tới bị loại bỏ và fallback chọn trúng `@username` (`t6f` hoặc `t3y`).
  - Hơn nữa, flow ưu tiên `display_name_anchor_element` (FrameLayout rỗng) trước `display_name_element` thật.
- **Quy tắc khắc phục:**
  - Ưu tiên `display_name_element` trước `display_name_anchor_element`.
  - Kiểm tra mép trên `bounds[1] <= 320` thay vì tâm `center[1] <= 320` để không bỏ sót header.

## 2. Full-Width Switcher Row Tap Offset (Tránh tap trượt x=540)
- **Hiện tượng:** Switcher sheet mở đúng, nhìn thấy đúng account đích nhưng tap xong TikTok không phản hồi, profile vẫn giữ nguyên nick cũ (ví dụ M78).
- **Nguyên nhân:**
  - Hàng tài khoản `com.ss.android.ugc.trill:id/ls_` trải dài toàn màn hình `[0, y1][1080, y2]`.
  - Tap mặc định vào tâm `(540, center_y)` rơi trúng khoảng trống giữa text tên nick và badge số thông báo `9+` (`p05`), không kích hoạt click listener của RecyclerView.
- **Quy tắc khắc phục:**
  - Với node switcher full-width (`bounds[0] == 0` và `bounds[2] >= 1000`), bắt buộc tap vào mép trái `x = 350` (hoặc thu hẹp bounds tap về `bounds[0] + 600`), nơi chứa avatar và text tên nick.

## 3. Samsung FOTA Occlusion Recovery (`com.wssyncmldm`)
- **Hiện tượng:** Popup cập nhật hệ thống / FOTA Samsung hiển thị đè màn hình (`com.wssyncmldm` activity `IDMUIDownloadConfirmDialog`), làm mất focus TikTok (ví dụ M261).
- **Quy tắc khắc phục:**
  - Thêm `com.wssyncmldm` vào nhóm `SYSTEM_OCCLUSION_PACKAGES` trong `flows/device_prepare.py`.
  - Gửi phím BACK (`input keyevent 4`) để đóng dialog FOTA, sau đó kiểm tra lại focus gói đích trước khi relaunch.

## 4. Bắt buộc Canary Gate sau khi Fix & Tránh Xung Đột Khóa Kép (`device_lock`)
- **Nguyên tắc Invariant:** Sau khi sửa code T1/L2, BẮT BUỘC chạy Canary trên 1 máy thật (chụp ảnh / log sạch) trước khi báo cáo hoàn thành.
- **Cạm bẫy Khóa Kép:**
  - Khi dùng `with_device_lock.py` bọc ngoài một lệnh runner nội bộ (`run_tiktok.py`), bản thân runner đó cũng có module acquire atomic `device_lock`.
  - Nếu `with_device_lock.py` giữ lock trước, runner con bên trong sẽ phát hiện thiết bị bị chiếm bởi chính wrapper -> `skipped-device-locked` và exit 2.
- **Quy tắc khắc phục:**
  - Sử dụng cờ `--no-lock` trên `with_device_lock.py` (ví dụ `python with_device_lock.py -m <N> --no-lock -- <runner_cmd>`) khi lệnh được bọc là một script tự quản lý `device_lock`.
