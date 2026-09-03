# Pitfall: TikTok SplashActivity Cold-Start & Large Screenshot Unknown State

## Triệu chứng
- Alert `[MÁY N]`: `unknown TikTok state` ngay tại baseline attempt 1.
- Màn hình chụp tối đen hoặc giữ khung hình launcher wallpaper cũ nhưng OS đang focus vào `SplashActivity` (`com.ss.android.ugc.trill/...SplashActivity` hoặc activity chứa `splash`).
- Dung lượng screenshot lớn (> 80KB), XML hierarchy trả về rỗng / không nhận diện được element -> state detection trả về `unknown`.

## Root Cause
- Hàm `_is_startup_loading_retry_row()` áp dụng size-gate `screenshot_size_bytes < 80_000` cho trường hợp `detected == "unknown"`.
- Khi máy cold-start chậm, screenshot frame chuyển cảnh có dung lượng lớn bị loại khỏi retry queue và fail-closed ngay lập tức thành `unknown TikTok state`.

## Giải pháp chuẩn hóa
1. Kiểm tra focus package & focus activity: nếu đang ở `SplashActivity` và `detected == "unknown"`, cho phép bounded retry 1 vòng thay vì ngắt session ngay.
2. Chỉ fail-closed nếu app ở `MainActivity` hoặc màn hình khác kèm screenshot lớn và state `unknown`.
3. Đảm bảo unit test bao phủ cả 2 nhánh (SplashActivity retry và MainActivity fail-closed) trước khi commit.
