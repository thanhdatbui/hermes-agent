# Kỷ Luật Fail-Closed TikTok, Bẫy Mangle Direct Leak & Screencap Anti-Black Screen (2026-11-06)

## 1. Bản chất nguy hiểm của TikTok TTNet Fail-Open khi chạy Kernel DNAT
- Khi sử dụng Singbox Container (`172.17.0.2`):
  - Singbox là L7 Application Proxy Server. Nó gom toàn bộ socket mạng của thiết bị vào container. Nếu proxy đầu xa bị chết, Singbox đóng kết nối TCP và ngắt hẳn luồng mạng -> Thiết bị hoàn toàn không có đường nào để chạm vào WAN của router.
- Khi chuyển sang **Kernel DNAT thuần túy trên MikroTik RouterOS**:
  - RouterOS hoạt động như một Router L3/L4 chuyển tiếp gói tin phần cứng.
  - Khi proxy đầu xa (MobiProxy hoặc R3G) bị sập, ngắt hoặc rớt mạng: Cổng HTTP proxy nội bộ (`192.168.110.2:20xxx`) không có phản hồi (`ERR_EMPTY_RESPONSE`).
  - **BẪY RÒ RỈ CỐT TỬ CỦA TIKTOK:** SDK mạng của TikTok (TTNet) có cơ chế tự động thử lại bằng UDP QUIC (port 443) hoặc tự động bypass proxy đẩy trực tiếp gói tin ra Default Gateway Wi-Fi.
  - Nếu router MikroTik vẫn còn các rule Mangle PBR (`FARM_ADMIN_MAY_xxx_TO_WANx`) gán cờ `mark-routing=WANx`, gói tin lách proxy của TikTok sẽ bị Mangle chộp lấy và ném thẳng ra các line PPPoE Viettel Đà Nẵng!
  - **Hậu quả:** App TikTok vẫn tải video bình thường (lướt clip cô gái, clip đồ ăn ầm ầm) bằng **CHÍNH IP GỐC CÁP QUANG ĐÀ NẴNG**, gây rủi ro cháy acc hàng loạt!

## 2. Giải pháp cơ học: Khóa cứng Fail-Closed trên RouterOS
Muốn đảm bảo nguyên tắc sống còn: **"PROXY SẬP THÌ TIKTOK PHẢI CHẾT THEO 100%"**, bắt buộc phải thiết lập:
1. **Khóa cứng Firewall Filter:**
   - Sửa rule `KILLSWITCH_BLOCK_FARM_DIRECT_WAN` (`*D`) thành `src-address=192.168.0.0/16 action=drop out-interface-list=WAN`.
   - VÔ HIỆU HÓA HOÀN TOÀN rule `*10` (`ALLOW_FARM_ADMIN_FORWARD_FPT_LAN`, set `disabled=true`): Đây là lỗ hổng chết người mở toang `FPT_LAN` (`192.168.110.0/24`) cho phép forward không giới hạn port, từng làm rò rỉ hơn 21.5 GB traffic direct ra ngoài. Chỉ cho phép các cổng proxy hợp lệ (`10001-10035, 20001-20280`) qua rule `*15` (`ALLOW_FPT_LAN_PROXY_PORTS`).
   - Kích hoạt lại rule `*9` (`KILLSWITCH_BLOCK_QUIC_UDP_443` -> `disabled=false`), mở rộng `src-address=192.168.0.0/16` cấm toàn bộ UDP 443 đi ra WAN.
2. **Khóa cửa RAW Prerouting (Stateless Killswitch trước Conntrack & Mangle):**
   - Nạp rule RAW Prerouting chém đứt QUIC ngay tại cửa vào router:
     `/ip firewall raw add chain=prerouting src-address=192.168.0.0/16 protocol=udp dst-port=443 action=drop comment="RAW_KILLSWITCH_DROP_QUIC_UDP443"`
   - Chỉ cho phép traffic từ farm tới đúng cổng Proxy nội bộ (`20001-20280`), toàn bộ traffic direct bypass còn lại bị chặn đứng trước khi bảng Mangle kịp gán cờ `mark-routing=WANx`.
   - Hễ proxy chết thì mọi gói tin bypass của TikTok đều bị tiêu diệt ngay tại router, app TikTok lập tức dừng hình, hiện màn hình báo lỗi mạng và nút đỏ "Thử lại".

## 3. Cạm bẫy S7 Display Sleep (Màn hình đen sì) & Lừa đảo Native Multimodal
- Điện thoại Samsung S7 tự động tắt màn hình (`Display Power: state=OFF`) sau 30-60 giây để tiết kiệm pin.
- Khi màn hình ở trạng thái `state=OFF`, lệnh `screencap` hoặc dump framebuffer trả về mảng pixel **hoàn toàn là số 0 (RGB = [0, 0, 0])**, ảnh lưu ra là **một hình chữ nhật đen sì 100%**.
- **LỖI VI PHẠM GATE 6 NẶNG NHẤT:** Gửi ảnh đen sì cho User nhưng lại tự bịa đặt mô tả ("Màn hình hiển thị không có kết nối mạng, nút đỏ Thử lại, dấu chấm than..."). Đây là hành vi lừa dối, ảo giác khi chưa nhìn thấy pixel thật.
- **Quy trình bắt buộc trước khi chụp ảnh màn hình S7:**
```bash
adb -s <serial> shell "input keyevent 224 && input keyevent 82 && svc power stayon true && settings put system screen_off_timeout 600000"
```
- **Hậu kiểm mảng màu pixel thật bằng Python trước khi gửi thẻ MEDIA:**
```python
import numpy as np
from PIL import Image

img = Image.open(image_path)
r, g, b, _ = img.split()
r_vals = np.unique(r)
g_vals = np.unique(g)
b_vals = np.unique(b)

if len(r_vals) == 1 and r_vals[0] == 0 and len(g_vals) == 1 and g_vals[0] == 0 and len(b_vals) == 1 and b_vals[0] == 0:
    raise RuntimeError("REJECTED: Màn hình điện thoại bị đen sì 100% (state=OFF), cấm gửi ảnh mù!")
```
