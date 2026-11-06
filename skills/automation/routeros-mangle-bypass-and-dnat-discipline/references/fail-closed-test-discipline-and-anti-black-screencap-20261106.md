# Sự Cố Lệch Luồng Fail-Closed Test & Bài Học Chống Ảnh Đen Kịt (2026-11-06)

## 1. Hiện trường sự cố thực tế
- **Yêu cầu của Operator:** Kiểm tra chứng minh thực tế cơ chế Fail-Closed: *"Khi proxy rớt mạng/sập thì máy S7 qua DNAT có mất mạng không? Mở TikTok trên máy đó xem có mạng không?"*
- **Sai lầm thao tác của Agent:**
  1. Tự ý tắt cổng proxy 5142 xong lại vội vã bật lại ngay trước khi chụp ảnh màn hình điện thoại Máy 204.
  2. Khi người dùng mở App TikTok, TikTok nhận lại mạng và tải video bình thường (cô gái mặc váy sọc đỏ trắng, video nấu tô thịt bò tái sốt tiêu). Người dùng gửi ảnh hỏi vặn lại: *"Tao bảo test lúc proxy sập thì máy có mạng không, mày làm cái gì thế?"*
  3. Khi chụp lại màn hình, điện thoại S7 đã rơi vào trạng thái ngủ (`Display Power: state=OFF` do timeout 30s). Lệnh `screencap` trả về một bức ảnh đen sì 100% (RGB: 0, 0, 0).
  4. Agent không kiểm tra mảng màu pixel thực tế, vội vàng gửi thẻ `MEDIA:` ảnh đen sì kèm lời mô tả suy đoán ảo giác trong đầu, vi phạm nghiêm trọng kỷ luật Gate 6 và làm Operator nổi giận.

## 2. Cạm bẫy TikTok Preload Video Cache & Cold Start Discipline
- **Cơ chế tải trước của TikTok:** App TikTok (TTNet client) luôn tự động preload 3-5 video kế tiếp vào RAM/bộ nhớ tạm. Khi ngắt proxy ngang, người dùng quẹt tiếp vài video vẫn thấy video phát mượt mà từ cache, dễ gây hiểu lầm là máy vẫn có mạng.
- **Biện pháp cô lập cache:**
  - Bắt buộc kiểm tra đồng thời qua trình duyệt web thuần TCP (`icanhazip.com` báo `ERR_CONNECTION_REFUSED` / `ERR_EMPTY_RESPONSE`).
  - Đối với TikTok: Bắt buộc force-stop (`am force-stop com.ss.android.ugc.trill`) rồi mới khởi động lại từ đầu (Cold Start) trong lúc proxy vẫn đang bị ngắt để triệt tiêu cache tạm.

## 3. Kỹ thuật khắc phục triệt để

### A. Quy trình kiểm tra Fail-Closed đúng chuẩn
1. Khóa cứng cấu hình DNAT của cổng cần test (ví dụ cổng `20204` của Máy 204).
2. Tắt cổng proxy trên router đầu xa (hoặc bẻ `to-addresses` trên MikroTik sang IP dead-end `192.0.2.1`).
3. Đánh thức màn hình điện thoại S7:
   ```sh
   adb -s <serial> shell "input keyevent 224 && input keyevent 82 && svc power stayon true && settings put system screen_off_timeout 600000"
   ```
4. Xác nhận màn hình đã sáng:
   ```sh
   adb -s <serial> shell "dumpsys power | grep -i 'Display Power'"
   # Bắt buộc trả về: Display Power: state=ON
   ```
5. Mở App TikTok hoặc trình duyệt:
   ```sh
   adb -s <serial> shell "am force-stop com.ss.android.ugc.trill && am start -n com.ss.android.ugc.trill/com.ss.android.ugc.aweme.splash.SplashActivity"
   ```
6. Chụp ảnh màn hình bằng chứng qua framebuffer:
   ```sh
   screencap /sdcard/raw.dump && adb pull /sdcard/raw.dump <local_dump>
   ```

### B. Kiểm tra mảng màu pixel chống ảnh đen mù (Anti-Black Check)
Trước khi gửi thẻ `MEDIA:`, bắt buộc chạy:
```python
import struct, numpy as np
from PIL import Image

with open('<local_dump>', 'rb') as f:
    w, h, fmt = struct.unpack('III', f.read(12))
    raw = f.read()

img = Image.frombytes('RGBA', (w, h), raw)
r, g, b, _ = img.split()
r_vals = np.unique(r)
g_vals = np.unique(g)
b_vals = np.unique(b)

if len(r_vals) == 1 and r_vals[0] == 0 and len(g_vals) == 1 and g_vals[0] == 0 and len(b_vals) == 1 and b_vals[0] == 0:
    raise RuntimeError("CẤM GỬI MEDIA: Ảnh bị đen kịt 100% do màn hình đang ngủ!")
```

### C. Soi mắt đọc nội dung thật bằng Native Multimodal
- Dùng mắt thần Native Multimodal đọc chi tiết từng chữ trên ảnh:
  - Thông báo: "Không có kết nối mạng" / "No internet connection".
  - Nút bấm: Nút đỏ "Thử lại".
  - Thanh trạng thái: Wi-Fi có dấu chấm than (!) màu đen nhỏ.
- Sau khi có đầy đủ ảnh bằng chứng thực tế mới tiến hành phục hồi lại cổng proxy về bình thường.
