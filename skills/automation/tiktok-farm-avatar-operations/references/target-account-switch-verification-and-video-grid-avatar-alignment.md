# Target Account Verification & Video Grid Avatar Alignment (2026-10-13)

## 1. Sự Cố & Bẫy Chết Người (Root Cause Analysis)

### 1.1. Bẫy Thao Tác Sai Tài Khoản Trong Môi Trường Multi-Account (False Positive Upload)
- **Hiện tượng**:
  - Trên thiết bị farm (Samsung S7, TikTok v47+), mỗi máy thường đăng nhập tới 8 tài khoản vật lý trong Account Switcher.
  - Script hoặc Agent vào màn hình Profile, bấm ngay nút "Sửa hồ sơ" -> "Thay đổi ảnh" -> tải ảnh lên -> báo cáo "THÀNH CÔNG 100%".
  - **Hậu quả nghiêm trọng**: Tài khoản đang active trên màn hình lúc đó **không phải tài khoản mục tiêu** (ví dụ active là `@mimiiepekgq` thay vì `@kieu.lam966`). Kết quả là đổi nhầm avatar của tài khoản khác, trong khi tài khoản mục tiêu trên server TikTok vẫn giữ nguyên avatar cũ/rác (như logo GDĐT). User kiểm tra thực tế trên điện thoại cá nhân thấy hoàn toàn chưa đổi, dẫn đến bức xúc và mất lòng tin.
- **Quy tắc Bắt Buộc (Target Account Verification Invariant)**:
  1. **Kiểm tra Handle trước khi thao tác**: Trước khi bấm "Sửa hồ sơ", BẮT BUỘC dump UI hoặc OCR kiểm tra `@username` đang hiển thị trên Profile có khớp 100% với tài khoản mục tiêu hay không.
  2. **Chuyển tài khoản qua Switcher nếu lệch**:
     - Nếu handle chưa khớp, tìm anchor Switcher (nút tên tài khoản / Button header ở Layout C hoặc dropdown ở Layout cũ).
     - Mở Switcher -> Tìm đúng tài khoản mục tiêu -> Tap chọn -> Đợi Profile tải lại và xác nhận lại `@username` đúng mới được tiến hành đổi avatar.

---

### 1.2. Bẫy Lệch Avatar So Với Lưới Video Đã Đăng (Channel Persona Drift)
- **Hiện tượng**:
  - Kênh đã đăng nhiều video (ví dụ chủ đề công sở `#congviec #vanphong` với nhân vật nữ mặc blazer / đeo kính tại bàn làm việc).
  - Agent hoặc tool tự động trích xuất frame từ video rác cũ (như slide bài giảng có huy hiệu GDĐT) hoặc lấy ảnh chân dung không hề xuất hiện trong các video đã đăng (như ảnh nữ sinh đeo ba lô hay áo phông hồng).
  - Khi người xem hoặc chủ kênh nhìn vào profile, avatar một người nhưng video lại là một người hoàn toàn khác.
- **Quy tắc Trích Xuất & Căn Chỉnh Avatar (Persona Alignment)**:
  1. **Soi mắt lưới video đã đăng (Video Grid First)**: BẮT BUỘC kiểm tra thumbnail của 3-6 video đầu tiên trên kênh (qua screenshot profile hoặc thư mục video nuôi).
  2. **Nhận diện chính chủ kênh**: Xác định rõ khuôn mặt, trang phục, giới tính và phong cách của nhân vật chính trong các video đã đăng.
  3. **Trích xuất đúng nhân vật**:
     - Chọn frame cận cảnh sắc nét, mỉm cười tự nhiên của đúng nhân vật đó (độ nét Laplacian variance cao).
     - Cắt vuông chuẩn tỉ lệ tròn TikTok (mặt chiếm 45-55% diện tích hình tròn, không cụt đầu, headroom hợp lý).
  4. **Đồng bộ SSOT vào cả 4 đầu thư mục**:
     - `D:/TIKTOK-videonuoinick/<F_out>/avatar.jpg`
     - `D:/video goc/<F_out>/avatar.jpg`
     - `D:/TIKTOK-videonuoinick/<F_src>/avatar.jpg`
     - `D:/video goc/<F_src>/avatar.jpg`
     (trong đó $F_{src} = (Slot - 1) \times 80 + M$).

---

## 2. Quy Trình Chạy Standalone Avatar Smoke Chuẩn Qua CLI

Để chạy đổi avatar an toàn và chuẩn hóa cho một máy cụ thể mà không chạm vào luồng đăng video:
```bash
echo AVATAR-SMOKE | python D:/Taadaa/Tiktok-video/scripts/run_workflow_cli.py \
  --config D:/CodexRuntime/tiktok-video/config-machine-62.yaml \
  --workflow-workbook D:/OneDrive/TaadaaData/kibe/Tik<Slot>.xlsx \
  --machine <M> \
  --avatar-smoke \
  --force-avatar-upload \
  --force-avatar-machines <M> \
  --verbose
```
- Cơ chế này:
  - Tự động khóa thiết bị qua `operator_device_lock`.
  - Mở app TikTok và gọi `automation_core.tiktok.account_switcher` để chuyển chính xác tài khoản mục tiêu.
  - Đẩy ảnh avatar từ nguồn chuẩn và thực hiện luồng đổi avatar.
  - Không bao giờ chạm vào trạng thái đăng video hay ghi đè sai workbook.
