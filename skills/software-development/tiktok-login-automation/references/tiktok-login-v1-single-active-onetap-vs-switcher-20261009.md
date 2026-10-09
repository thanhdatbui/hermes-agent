# TikTok Login v1 Single-Active Fast-Login (One-tap) vs Multi-Session Switcher Behavior

## Bối cảnh thực tế (Session 2026-10-09 - Máy 266 / TikTok v46.6.3 trên Samsung S7)
Khi một máy Android farm gặp hiện tượng không bung được **Account Switcher** (menu trượt danh sách tài khoản từ đáy màn hình) dù trên máy đã lưu nhiều tài khoản (ví dụ Máy 266 có `letam2502` và `bongbong02892`), nguyên nhân và cơ chế phân định như sau:

---

### 1. Phân biệt Multi-Session Active Switcher vs Single-Session One-Tap Login
1. **Multi-Session Active Switcher (App có >= 2 session active đồng thời)**:
   - Header Profile: Xuất hiện nút Chevron ▼ bên cạnh tên hiển thị.
   - Khi bấm vào tên / chevron: App bung bottom sheet **Account Switcher** (`com.ss.android.ugc.trill:id/n72` / danh sách account).
   - Menu Cài đặt & quyền riêng tư: Ở đáy có dòng **"Chuyển đổi tài khoản"** (Switch account).

2. **Single-Session Active / Fast-Login Only (Chỉ có 1 session active trong app)**:
   - Header Profile: Tên hiển thị chỉ là text tĩnh (node `sv6`), **hoàn toàn KHÔNG CÓ nút mũi tên ▼**.
   - Bấm vào tên: Không mở Switcher; bấm trúng vùng text có thể kích hoạt widget gắn vị trí / chủ đề (Theme/Map/Location).
   - Menu Cài đặt & quyền riêng tư: Ở đáy **CHỈ CÓ NÚT "Đăng xuất"**, hoàn toàn không có mục "Chuyển đổi tài khoản".
   - **Màn hình trung tâm quản lý tài khoản lúc này**: Là màn hình **One-tap Login ("Chào mừng bạn trở lại" / Welcome Back)** xuất hiện sau khi Đăng xuất hoặc bấm "Đăng nhập" ở tab Hồ sơ.

---

### 2. Hành vi & Quy trình kích hoạt lại Session
- Khi cả 2 tài khoản bị văng session (hoặc 1 tài khoản chưa gộp vào multi-session pool), TikTok lưu giữ thông tin tại màn hình Fast Login:
  - Header: `Chào mừng bạn trở lại` (`com.ss.android.ugc.trill:id/title`)
  - Danh sách các nick lưu phiên: `@account1`, `@account2` kèm email ẩn danh (`yrj`).
  - Nút chuyển hướng: `Thêm tài khoản khác` (`com.ss.android.ugc.trill:id/desc`) và `Bạn không có tài khoản? Đăng ký` (`com.ss.android.ugc.trill:id/nys`).
- **Cách chuyển đổi / kích hoạt**:
  1. Nếu muốn vào nick đã lưu: Chạm trực tiếp vào hàng chứa tên nick (`bounds` tương ứng) $\rightarrow$ TikTok nạp session và đưa thẳng vào Profile mà không cần pass/OTP.
  2. Nếu muốn gộp session thành Multi-session active để app hiện lại Switcher: Bắt buộc phải thông qua luồng **"Thêm tài khoản khác"** $\rightarrow$ chọn *"Sử dụng Email/Username"* $\rightarrow$ nạp pass hoặc OTP để TikTok liên kết token mới vào cùng active session pool của app.

---

### 3. Cập nhật CLI & Môi trường khi chạy `tiktok_login_v1.py` trên cụm Admin (Máy 201-280)
- **Cấu hình ADB Server Socket bắt buộc**:
  Khi chạy cho dàn Admin từ host Kibe, bắt buộc nạp biến môi trường socket cụm Admin:
  ```bash
  ADB_SERVER_SOCKET="tcp:192.168.110.119:5037" TAADAA_HOST_CONFIG="D:/Taadaa/machine-config/admin.yaml" python -u D:/Taadaa/Tiktok_Reg/tiktok_login_v1.py <STT> --email <ID/email> --ss
  ```
- **Fallback Tra cứu Thiết bị**:
  Hàm `resolve_device(stt)` trong `tiktok_login_v1.py` đã có cơ chế fallback sang `load_machine_devices(TARGET_INVENTORY_WORKBOOK)` (`taikhoan_run_safe.xlsx`) cho các máy ngoài dải 1-80 (`STT >= 201`).
