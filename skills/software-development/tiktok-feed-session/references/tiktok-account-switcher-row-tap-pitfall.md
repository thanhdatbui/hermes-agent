# TikTok Account Switcher Row Tap Dead-Zone Pitfall & Race Condition

## Bối cảnh & Hiện tượng (Incident Run 20260907-035747 trên Máy 79)
- Script: `feed-session-smoke` (trong `python_runner/flows/feed_swipe_smoke.py`).
- Hiện tượng: Script phát hiện sai tài khoản trên profile (`Vy Bống` / `@refughbmh33`), mở switcher bottom sheet (`Chuyển đổi tài khoản`), tìm thấy tài khoản đích `ruffumyxkvv`, thực hiện tap `tap_expected_account` thành công nhưng sau đó TikTok vẫn không đổi tài khoản (`Dấu kiểm` id/fdu vẫn ở nguyên `@refughbmh33`). Script thử lại lần 2 vẫn kẹt và dừng với trạng thái `manual-needed`.

## Root Cause 1: Lệch tọa độ tap do lấy center của row Button full-width (`id/l9b`)
Cấu trúc UI XML của account switcher bottom sheet (`com.ss.android.ugc.trill:id/fsd`):
```xml
<androidx.recyclerview.widget.RecyclerView bounds="[0,576][1080,1920]">
  <android.widget.Button rid="com.ss.android.ugc.trill:id/l9b" cdesc="ruffumyxkvv" bounds="[0,816][1080,1032]" clickable="true">
    <!-- Vùng avatar: x khoảng [0, 252] -->
    <android.widget.TextView rid="com.ss.android.ugc.trill:id/mtx" text="ruffumyxkvv" bounds="[252,894][543,954]" clickable="false" />
    <!-- Vùng trống bên phải: x từ [543, 1080] -->
  </android.widget.Button>
</androidx.recyclerview.widget.RecyclerView>
```
- **Pitfall**: Khi script selector match vào thẻ bao `id/l9b`, nó lấy trung tâm `bounds=[0,816][1080,1032]`, tính ra tọa độ `center = (540, 924)`.
- Tọa độ `x=540` rơi đúng vào **mép ngoài cùng bên phải của TextView `id/mtx`** (`543`) hoặc vùng trống vô hình. Trên nhiều phiên bản TikTok, touch event ở vùng rìa trống này bị nuốt hoặc không kích hoạt event chọn tài khoản của item.

### Quy tắc định vị tọa độ tap trong Switcher Sheet:
1. **Ưu tiên tap vào vùng text hoặc avatar:**
   - Tap vào tâm của `TextView` username (`id/mtx`): `center_x ≈ 397`.
   - Hoặc tap vào vùng avatar/nội dung phía bên trái: `x ≈ 150..350`, `y = center_y`.
2. **CẤM lấy center của container full-width (`x=540`):** Luôn clamp `center_x` về `min(center_x, 350)` hoặc dùng trực tiếp bounds của node text username `id/mtx`.

## Root Cause 2: Race Condition điều hướng (Tap Profile ngay sau Switch)
- Ngay sau lệnh tap switch tài khoản, runner gửi tiếp lệnh tap vào tab Profile ở navigation bar đáy (`bounds: [864,1794][1080,1920]`, center `[972, 1857]`).
- Việc tap navigation ngay lập tức sẽ đóng bottom sheet trước khi TikTok hoàn tất chuyển đổi phiên đăng nhập hoặc trước khi switch request kịp gửi đi.
- **Quy tắc:**
  - Sau khi tap chọn tài khoản trong sheet, BẮT BUỘC đợi bottom sheet tự đóng hoặc đợi UI transition (khoảng 1.5s - 3s).
  - Không gửi phím Back hay tap tab Profile bừa bãi khi sheet đang trong quá trình chuyển đổi.
  - Kiểm tra dấu kiểm (`Dấu kiểm`, `id/fdu`) hoặc reload profile để xác nhận username đã khớp trước khi tiếp tục flow.
