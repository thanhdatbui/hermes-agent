# Quy Trình Tự Chủ Đổi Avatar Hàng Loạt & Nguyên Tắc Tự Chọn Phương Án (Autonomous Multi-Account Avatar Operations)

## 1. Tín Hiệu Chỉ Đạo Của Operator & Nguyên Tắc Tự Chủ (Autonomy Invariant)
- **Bối cảnh thực tế (15/10/2026)**: Khi User gửi ảnh chụp màn hình hồ sơ TikTok kèm lệnh *"Đổi ava 3 nick này"*, Coordinator trích xuất ứng viên, tạo preview viền tròn xanh rồi hỏi User chọn Option 1 hay Option 2. User phản hồi dứt khoát: ***"Tự chọn r làm đi"***.
- **Nguyên tắc hành động cốt lõi**:
  - Khi User giao việc đổi avatar cho nhiều nick, Operator kỳ vọng Coordinator **TỰ ĐÁNH GIÁ, TỰ CHỌN PHƯƠNG ÁN TỐI ƯU VÀ THỰC THI TOÀN TRÌNH DỨT ĐIỂM**, không hỏi dền dứ các quyết định vi mô khi Agent đã có đầy đủ công cụ Vision để tự thẩm định.
  - Vẫn xuất và lưu đầy đủ ảnh bằng chứng `preview_<nick>.jpg` và đính kèm `MEDIA:` trong báo cáo để đảm bảo tính minh bạch (Gate 6), nhưng không dừng chờ User duyệt từng tấm mới bắt đầu chạy runner.

---

## 2. Tiêu Chí Tự Động Chấm Điểm & Lựa Chọn Avatar Tối Ưu (Autonomous Selection Criteria)
Khi có 2 hoặc nhiều khung hình ứng viên từ video, Coordinator tự động chọn phương án đạt điểm cao nhất theo 4 tiêu chí khắt khe:

1. **Góc Nhìn & Hướng Mắt (Frontal Gaze Priority)**:
   - Ưu tiên góc chụp chính diện (frontal) hoặc nghiêng nhẹ (3/4), mắt nhìn thẳng hoặc hướng về phía camera.
   - **Loại bỏ ngay**: Khoảnh khắc nhắm mắt/chớp mắt khi đang nói, cúi đầu, quay lưng, góc nghiêng gắt (>45 độ) hoặc biểu cảm gượng gạo/căng thẳng.
2. **Đúng Nhân Vật Đại Diện Theo Niche (Subject Fidelity)**:
   - Khớp 100% với chủ đề kênh thực tế (ví dụ: Nữ MC cho bản tin thời sự/tài chính, điều dưỡng/người lớn cho dịch vụ mẹ và bé, diễn giả mặc vest cho kênh kinh doanh/tư duy).
   - Áp dụng quy tắc ưu tiên nữ (`AIFemaleFilter`) nếu kho video kênh có sự xuất hiện của nhân vật nữ.
3. **Tuân Thủ Tuyệt Đối Invariant Headroom ($cy \approx 0.2 \times H$)**:
   - Đỉnh tóc/vòm đầu cách mép trên vòng tròn một khoảng thở an toàn khoảng **30–40px** (tương đương 8–10% đường kính).
   - CẤM TUYỆT ĐỐI chọn frame mà đỉnh đầu chạm sát mép hoặc bị cắt ngang qua chân tóc/đỉnh trán khi lên khung tròn TikTok.
4. **Độ Sạch Khung Hình (Visual Cleanliness)**:
   - Không bị dính logo watermark rác của nền tảng khác.
   - Không bị chữ phụ đề (subtitle/caption) chạy ngang qua ngực hoặc che một phần cằm/mặt.
   - Không có sticker, emoji hay icon đè lên da mặt.

---

## 3. Quy Trình Đồng Bộ Toàn Diện 5 Điểm (5-Point Full Synchronization)
Sau khi đã chọn được avatar tối ưu, bắt buộc thực hiện đồng bộ khép kín 5 điểm trước và trong khi chạy runner:

### Điểm 1: Đồng Bộ Kho Kép (Dual-Store & Dual-Folder Copy)
File `avatar.jpg` chuẩn vuông $512 \times 512$ phải được copy vào CẢ folder gốc ($F_{src}$) và folder render ($F_{out}$) tại CẢ 2 đầu kho đĩa:
1. `D:/video goc/<F_src>/avatar.jpg`
2. `D:/video goc/<F_out>/avatar.jpg`
3. `D:/TIKTOK-videonuoinick/<F_out>/avatar.jpg`
*(Đảm bảo mọi script dù đọc theo $F_{src}$ hay $F_{out}$ đều nhận diện đúng avatar mới).*

### Điểm 2: Khóa Bảo Vệ Cứng (SSOT Protection Registry)
Ghi ngay vào danh sách bảo vệ vĩnh viễn ở CẢ 2 file cấu hình để chống các script tự động (`_make_avatar.py`, `regenerate_unique_avatars.py`) quét đè:
- `D:/Taadaa/data/manual_avatar_protected_folders.json`
- `D:/Taadaa/Tiktok-video/data/manual_avatar_protected_folders.json`
- Thêm cả 2 số folder ($F_{src}$ và $F_{out}$) vào mảng `protected_folders` và bổ sung metadata chi tiết vào dictionary `accounts`.

### Điểm 3: Cập Nhật Trạng Thái Workbook Excel
- Mở file `D:/OneDrive/TaadaaData/kibe/Tik<Slot>.xlsx` (hoặc cụm Admin tương ứng).
- Tìm dòng của tài khoản mục tiêu, đặt giá trị cột `Avatar` (thường là Cột 13) thành `PENDING` (thay vì `OK`) để bộ lọc runner nhận diện.

### Điểm 4: Kích Hoạt Hàng Đợi Database (SQLite Queue)
- Upsert vào bảng `avatar_replace_queue` trong `D:/Taadaa/tiktok_tracker.db`:
  ```sql
  INSERT INTO avatar_replace_queue (may, tik, username, status, video_goc, folder_video, updated_at)
  VALUES (?, ?, ?, 'PENDING', ?, ?, datetime('now', 'localtime'))
  ON CONFLICT(may, tik) DO UPDATE SET
      status='PENDING', video_goc=excluded.video_goc, folder_video=excluded.folder_video, last_error=NULL, updated_at=datetime('now', 'localtime');
  ```

### Điểm 5: Khởi Chạy Runner Đơn Máy & Phân Tầng Cứu Hộ Không Đóng Băng (Non-blocking Batch Continuity)
- Khởi chạy runner đơn máy:
  ```powershell
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:/Taadaa/Tiktok-video/run_tiktok_upload_avatar.ps1 -Tik <Slot> -ForceAvatarMachineList <M> -MaxParallel 1
  ```
- **Xử lý sự cố lệch tài khoản / Switcher kẹt**:
  - Nếu runner báo `[ACCOUNT_SWITCHER_FAILED] SWITCHER_NOT_CONFIRMED`: Kiểm tra ngay screencap hiện trường. Nếu máy đang ở Profile của tài khoản khác (ví dụ máy 31 đang ở nick `@lu.huyn926`), runner cần đưa về đúng tài khoản của Slot mục tiêu.
  - Nếu thiết bị rớt kết nối USB transport (`device not found`): Gọi ngay `python D:/Taadaa/tools/recover_stuck_s7.py --machine <M>`.
  - **KỶ LUẬT TIẾP TỤC HÀNG ĐỢI (CONTINUITY INVARIANT)**: Khi một máy bị kẹt hoặc mất kết nối, CẤM đóng băng toàn bộ phiên; Coordinator ngay lập tức khởi chạy runner cho các máy sẵn sàng tiếp theo trong danh sách (như Máy 55, Máy 65) để duy trì tiến độ farm, sau đó quay lại cứu hộ máy kẹt khi đường truyền ổn định.
