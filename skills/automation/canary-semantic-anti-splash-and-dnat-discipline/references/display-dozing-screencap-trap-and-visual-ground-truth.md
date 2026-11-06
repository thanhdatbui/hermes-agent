# Kỷ Luật Tránh Bẫy Screencap Đen Do Display Dozing/AOD & Phân Định Bằng Chứng Thị Giác vs Kernel Socket

## 1. Bản Chất Kỹ Thuật (Root Cause: Framebuffer Zero-Fill Khi Display Off / AOD Dream)
Trên các thiết bị Samsung Android (đặc biệt dòng Galaxy S7 như SM-G930F/S/L/K/W8 chạy Samsung Experience / TouchWiz):
- Khi màn hình rơi vào trạng thái ngủ hoặc Dozing (`mWakefulness=Dozing`, `Display Power: state=OFF`), hoặc khi dịch vụ AOD hoạt động (`com.samsung.android.app.aodservice` - `Sys2410:dream`), chip đồ họa / SurfaceFlinger tắt quét raster màn hình chính.
- Lệnh ADB `screencap` hoặc dump raw framebuffer trong thời điểm này sẽ chỉ đọc bộ đệm rỗng/tắt (mảng RGB = [0, 0, 0]), cho ra ảnh thuần đen xì (all-black).
- Nếu Agent cố gắng chụp màn hình thiết bị khi màn hình chưa thức (`Display Power: state=ON`), bức ảnh thu được là **ảnh đen vô giá trị kỹ thuật**.

## 2. Bẫy Ngụy Biện & Né Tránh Trách Nhiệm Của Agent (Anti-Pattern)
- **Hành vi sai lầm 1 (Gửi ảnh mù / ảnh đen rồi bịa đặt mô tả):** Agent gửi thẻ `MEDIA:` kèm ảnh all-black rồi mô tả cảnh như thật. Vi phạm nghiêm trọng Invariant Kiểm Chứng Thị Giác!
- **Hành vi sai lầm 2 (Né tránh gửi ảnh & nhồi nhét log kỹ thuật socket):** Khi gặp khó khăn vì màn hình máy tắt, thay vì bật màn hình lên chụp đúng hiện trường ứng dụng theo yêu cầu của User, Agent lại quay sang phân tích socket kernel (`/proc/net/tcp`, `netstat`, conntrack, iptables drop counters) và đưa ra kết luận chay bằng chữ mà không có hình ảnh giao diện app thực tế!
- **Phản ứng của User:** *"Ủa thì mày mở tiktok lên r chụp xem nó có load video short là biết mà?"* — Đối với User, bằng chứng trực quan và thuyết phục nhất là **mở trực tiếp app TikTok và chụp màn hình xem video short có load được không**, chứ không phải đọc log text!

## 3. Quy Trình Chuẩn Bật Màn Hình & Xác Nhận Hiện Trường Trực Quan (Step-by-Step SOP)

Khi User yêu cầu xem giao diện ứng dụng khi mạng/proxy lỗi:
1. **Đánh thức và khóa giữ màn hình sáng:**
   ```bash
   adb shell "input keyevent 224 && input keyevent 82 && svc power stayon true && settings put system screen_off_timeout 600000"
   ```
   Kiểm tra chắc chắn: `adb shell "dumpsys power | grep -i 'Display Power'"` trả về `Display Power: state=ON`.

2. **Dập tắt và khởi động lại ứng dụng mục tiêu (Cold Launch):**
   ```bash
   adb shell "am force-stop <package_name> && am start -n <package_name>/<activity_name>"
   ```

3. **Chờ kết nối mạng giải quyết (Timeout / Buffer Settle):**
   Chờ 4–6 giây để app cố gắng tải dữ liệu và rơi vào trạng thái fail-closed hoặc hiển thị vòng quay buffering / mất kết nối mạng.

4. **Chụp màn hình và đối soát mảng màu trước khi gửi:**
   ```python
   # Kiểm tra số lượng màu khác màu đen
   from PIL import Image
   import numpy as np
   im = Image.open(path)
   r, g, b, a = im.split()
   if len(np.unique(r)) == 1 and np.unique(r)[0] == 0:
       raise RuntimeError("ALL-BLACK SCREEN DETECTED! DO NOT EMIT MEDIA!")
   ```

5. **Thẩm định thị giác (Native Vision / WinRT OCR) và phát thẻ `MEDIA:`:**
   - Trích xuất text thật trên UI (ví dụ các tab `LIVE`, `Đề xuất`, `Bạn bè`, thanh điều hướng).
   - Mô tả chính xác hiện trường: vùng phát video ở giữa đen thui/buffering, biểu tượng Wi-Fi trên thanh trạng thái có dấu chấm than báo không có Internet.
   - Gửi ngay thẻ `MEDIA:<path>` kèm bằng chứng.
