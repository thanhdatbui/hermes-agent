# TikTok Avatar: Active Account Pre-Verification, Multi-Account Switcher Anchor in Layout C & Dispatch Contract Invariants (2026-10-13)

## 1. Hiện Tượng & Căn Nguyên (Root Cause Analysis)

### 1.1. Lỗi Đổi Nhầm Tài Khoản (False Target Avatar Mutation)
- **Hiện tượng**: Script báo cáo đã đổi avatar thành công 100%, có ảnh chụp profile nghiệm thu với avatar mới, nhưng khi kiểm tra tài khoản mục tiêu (`@kieu.lam966`) trên TikTok thật (iOS/Web/CDN), avatar vẫn nguyên vẹn hình ảnh cũ (logo GDĐT).
- **Căn nguyên**: Trên máy farm (mỗi máy chứa 8 tài khoản), runner khởi chạy TikTok và vào thẳng tab Hồ sơ -> Sửa hồ sơ -> Thay đổi ảnh mà **KHÔNG kiểm tra tài khoản đang active**. Kết quả là runner đã đổi avatar của một tài khoản khác đang mở sẵn trên thiết bị (`@mimiiepekgq` / `@kieuoanh.beauty`), trong khi tài khoản mục tiêu `@kieu.lam966` hoàn toàn chưa được chạm tới.

### 1.2. Vị Trí Switcher Anchor Trên Layout C (Bong Bóng Note)
- Trên Layout C (Avatar nằm góc trên bên phải `[708,300][1080,636]` kèm bong bóng Note "Tám chuyện nào"):
  - Thanh header trên cùng không có dropdown arrow truyền thống ở giữa.
  - **Nút mở Switcher thực tế:** Là Button chứa Tên hiển thị nằm ở góc trên bên trái:
    - `resource-id`: `com.ss.android.ugc.trill:id/t7l`
    - `bounds`: `[36, 280][567, 364]` (tọa độ tap an toàn: `(300, 320)`).
  - Tapping vào button này sẽ kích hoạt bottom sheet Account Switcher (`is_switcher_open == True`).

---

## 2. Quy Trình Tiền Kiểm Tra & Chuyển Nick Bắt Buộc (Pre-Mutation Invariant)

Trước khi thực hiện bất kỳ thao tác sửa hồ sơ hoặc thay đổi avatar:

1. **Dump UI & Xác nhận Identity**:
   ```python
   xml_text = dump_current_ui(client)
   # Kiểm tra xem handle @target_username có hiện diện trên Profile hay không
   if f"@{target_username.lstrip('@')}" not in xml_text:
       # BẮT BUỘC MỞ SWITCHER ĐỂ CHUYỂN NICK
       open_and_switch_account(client, target_username)
   ```

2. **Mở Switcher & Chọn Nick Chuẩn Xác**:
   - Nếu ở Layout C: Tap button `com.ss.android.ugc.trill:id/t7l` tại `(300, 320)`.
   - Nếu ở Layout Cũ: Tap header anchor `find_switcher_anchor(xml_text)`.
   - Quét danh sách account trong switcher (`list_accounts(xml)`).
   - Nếu tài khoản mục tiêu chưa hiển thị: vuốt nhẹ danh sách (`input swipe 540 1400 540 800 300`) để nạp thêm items.
   - Tap chính xác vào node chứa `target_username`. Chờ 3-5 giây để TikTok chuyển profile.
   - Dump UI lần nữa để xác nhận `@target_username` đã là active profile trước khi bấm "Sửa hồ sơ".

3. **Chụp Ảnh Đối Soát Pre-Action**:
   - Lưu ảnh profile trước khi đổi vào `/data/local/tmp/` (tránh MediaStore clutter).
   - Kéo về PC kiểm chứng bằng WinRT OCR hoặc vision để lưu vết đối soát.

---

## 3. Quy Tắc Guard Khi Điều Phối Subagent (`delegate_task`)

Khi Coordinator hết ngân sách T1 và dispatch Worker sửa script / thao tác farm:
- **Định dạng FILE tuyệt đối:**
  - Viết trực tiếp: `FILE: D:/Taadaa/tmp/execute_change_avatar_m20.py`.
  - **CẤM TUYỆT ĐỐI** bọc bằng ngoặc nhọn `<<< D:/... >>>` vì regex guard sẽ đọc cả dấu `<<<` dẫn đến lỗi `PATH_NOT_ABSOLUTE`.
  - **CẤM TUYỆT ĐỐI** viết đường dẫn sau gạch đầu dòng `- ` (ví dụ: `- D:/...`).
- **Focused Test Bắt Buộc:**
  - Phải có dòng `FOCUSED_TEST: python -m py_compile D:/Taadaa/tmp/execute_change_avatar_m20.py` hoặc pytest tương ứng.
