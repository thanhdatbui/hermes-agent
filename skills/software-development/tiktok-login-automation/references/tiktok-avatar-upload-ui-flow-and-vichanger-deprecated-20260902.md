# TikTok Avatar Upload Flow & ViChanger Deprecation (2026-09-02)

## 1. ViChanger VPN App Deprecation
- Farm đã chuyển đổi 100% sang cấu hình **Wi-Fi proxy qua MikroTik / Singbox cấp router** (`192.168.110.2:9090`, Singbox port `20001..20080`).
- App ViChanger trên các máy Android không còn được sử dụng để duy trì kết nối VPN.
- **Quy tắc Code:** Bỏ toàn bộ preflight `require_android_vpn` bắt buộc kiểm tra ViChanger app trong các runner (`tiktok-log-in`, `account_reconcile.py`, `account_inventory.py`) để tránh lỗi giả `VICHANGER_VPN_NOT_CONNECTED`.

## 2. Quy trình Upload Avatar TikTok trên UI mới & Onboarding Cards
- **Các điểm vào màn Sửa hồ sơ / Upload ảnh:**
  1. **Nút "Thêm ảnh" trên thẻ onboarding:** Tọa độ `[576, 1541][984, 1637]` (tâm `(780, 1589)`).
  2. **Nút Bút chì (Edit Profile) layout mới:** Tọa độ `[777, 510][921, 594]` (tâm `(849, 552)`).
  3. **Vòng tròn Avatar Profile Root:** Tap `(850, 400)` hoặc `(540, 580)`.
- **Thao tác trong Photo Picker ("Gần đây"):**
  - Tap vào ô checkbox tròn góc trên-phải của thumbnail ảnh đầu tiên: `resource-id` chứa `igm` hoặc tọa độ `(203, 288)`.
  - Tap nút **"Tiếp"** (hoặc "Tiếp (1)"): `resource-id="xip"` / `o_9` / tọa độ `(912, 1842)`.
- **Thao tác màn hình Cắt ảnh (Crop Screen):**
  - **Bỏ chọn Đăng lên Nhật ký (Story):** Kiểm tra `CheckBox` có text "Đăng ảnh này lên Nhật ký" (`id/sdb` / `(84, 1590)`), nếu `checked="true"` -> tap để untick.
  - **Lưu ảnh:** Tap nút **"Lưu"** (`id/tv_confirm` / `(792, 1794)`).
  - **Xác nhận Modal "Lưu và đăng":** Nếu xuất hiện popup modal xác nhận ở chân màn hình, tap nút "Lưu và đăng" tại `(540, 1764)`.
- **Dọn dẹp popup sau khi lưu:**
  - Sau khi lưu, TikTok có thể hiện popup "Thêm chương trình gây quỹ" (Add fundraiser) hoặc "Nhận thông báo từ các tài khoản khác":
    - Tap nút đóng góc trên trái `(84, 150)` hoặc nút **"Để sau"** `(312, 1758)`.
    - Tap lại tab **"Hồ sơ"** `(972, 1857)` để xác nhận giao diện Profile đã mất thẻ "Thêm ảnh hồ sơ" và chuyển sang trạng thái hoàn tất.

## 3. Kiểm tra nhanh Gmail Live qua CDP Web Tool
- Khi kiểm tra trạng thái Gmail, ưu tiên chạy trực tiếp qua `checkmail.live` trên Chrome CDP (`http://127.0.0.1:9222`) với API key `8f1e941c7398320f1988aa0cbcd9171c` thay vì chạy probe nặng trên thiết bị.
- Code tương tác: `window.editor.setValue(email)`, `window.liveResultEditor.setValue('')`, `document.getElementById('btn-check').click()`, đọc kết quả từ `window.liveResultEditor.getValue()`.
