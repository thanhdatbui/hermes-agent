# SplashActivity Focus & Large Screenshot Startup Retry Pattern (Case 82)

## Hiện tượng (Machine 34 Alert `unknown TikTok state`)
- Khi TikTok cold-start trên Android, thiết bị chuyển focus sang `com.ss.android.ugc.trill/...SplashActivity`.
- Tại frame splash/cold-start ban đầu, màn hình hiển thị màn hình đen hoặc frame hình nền tĩnh có dung lượng file ảnh chụp lớn (>80KB, ví dụ 763KB), trong khi UI hierarchy dump (`ui.xml`) trả về rỗng / không có node phân loại.
- Hệ thống classify màn hình là `detected == unknown`.

## Anti-Pattern
- `_is_startup_loading_retry_row()` trước đây kiểm tra điều kiện retry cho `detected == unknown` bằng gate kích thước screenshot `0 < size < 80_000` bytes.
- Khi frame splash đen có dung lượng vượt quá 80KB, điều kiện retry bị từ chối (`False`), khiến flow baseline dừng ngay lập tức sau 1 attempt với trạng thái fail-closed `unknown TikTok state` thay vì chờ thêm 1-2 nhịp recapture có kiểm soát.

## Giải pháp chuẩn (Standard Pattern)
1. **Kiểm tra Splash Activity Focus trước Size-Gate:**
   ```python
   def _is_splash_launch_focus(ctx: DeviceContext, row: dict[str, Any]) -> bool:
       expected_package = str(ctx.config.get("tiktok_package", "com.ss.android.ugc.trill"))
       focused_package = str(row.get("focus_package") or row.get("focused_package") or "")
       if focused_package != expected_package:
           return False
       focused_activity = str(row.get("focus_activity") or row.get("focused_activity") or "").lower()
       return "splash" in focused_activity
   ```
2. **Cho phép Bounded Retry khi ở Splash:**
   - Trong `_is_startup_loading_retry_row()`: nếu `_is_splash_launch_focus()` trả về `True`, cho phép retry (`return True`) bất kể dung lượng file ảnh.
   - Các activity khác (như `MainActivity`) khi gặp `detected == unknown` kèm ảnh lớn vẫn giữ nguyên fail-closed (`return False`) để chống loop vô tận khi thực sự kẹt màn lạ.
