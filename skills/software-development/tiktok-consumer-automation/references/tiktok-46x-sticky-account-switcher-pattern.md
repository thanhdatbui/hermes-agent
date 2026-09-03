# TikTok 46.x Profile Header Sticky Account Switcher Pattern

## 1. Hiện tượng & Vấn đề
Trên TikTok 46.x (giao diện Profile cá nhân mới), mũi tên dropdown ▼ bên phải tên (`rv5`) hoặc username (`rz5`/`sj8`) không phản hồi khi tap trực tiếp ở vị trí mặc định giữa màn hình, hoặc thanh chuyển tài khoản bị ẩn.

## 2. Giải pháp kỹ thuật chuẩn (Canonical UI Navigation)
1. **Cơ chế Sticky Bar:** Khi vuốt trang Profile lên 400px (`input swipe 540 1000 540 600 400`), thanh tiêu đề Profile sẽ thu gọn và ghim cố định thành **Sticky Switcher Bar** ở sát mép trên màn hình (vùng y <= 350px).
2. **Resource-ID nhận diện:**
   - Node `com.ss.android.ugc.trill:id/pcs` (hoặc các biến thể `p01`, `p1j`, `qx0`, `qzr`).
   - Bounds trung tâm: `(540, 150)`.
3. **Thứ tự thực thi trong code automation (`social_reg_v1.py` / `account_switcher.py`):**
   - **Pass 0:** Quét tìm node sticky top bar (`y <= 350`) -> Tap mở bottom sheet `Chuyển đổi tài khoản`.
   - **Fallback Swipe:** Nếu chưa xuất hiện node sticky và dropdown chưa mở -> Gọi `swipe(device_id, 540, 1000, 540, 600, 400)` để kích hoạt sticky bar trước lần thử kế tiếp.
   - Khi dropdown mở -> Tiến hành tap `Thêm tài khoản` (`com.ss.android.ugc.trill:id/ldd` tại `(540, 1788)`).
