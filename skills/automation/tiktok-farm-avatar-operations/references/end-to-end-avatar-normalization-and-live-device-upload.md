# Quy Trình Chuẩn Hoá Kênh End-to-End & Nạp Trực Tiếp Lên Thiết Bị Thật (2026-10-16)

## 1. Bản Chất Sự Cố & Kỷ Luật "Không Chờ Giục" ("Sao đéo tự làm mà t phải nhắn nữa")
- **Nguyên nhân gây bức xúc cho Operator:** Khi User gửi ảnh profile và yêu cầu *"Chuẩn hoá kênh này / 2 kênh này"*, Coordinator chỉ thực hiện trích xuất ảnh, căn chỉnh Headroom 512x512, cập nhật file Excel/marker rồi gửi báo cáo lý thuyết và dừng lại. Việc này khiến tài khoản trên điện thoại thật vẫn giữ avatar cũ (lỗi dính chữ, lệch ngách), buộc User phải nhắn hỏi *"Xong chưa"* và bức xúc *"sao đéo tự làm"*.
- **Quy tắc bất di bất dịch:** Lệnh chuẩn hoá kênh (Chuẩn hoá 3 món: Avatar – Hashtag – Pin) là quy trình khép kín **End-to-End** từ file dữ liệu đến màn hình app thật trên thiết bị. Coordinator **BẮT BUỘC TỰ ĐỘNG THỰC THI LIÊN TỤC** đến khi ảnh đại diện mới được nạp thành công lên app TikTok trên điện thoại và có ảnh chụp màn hình kiểm chứng thị giác thực tế.

---

## 2. Quy Trình Khép Kín 4 Bước Chuẩn Hoá Kênh

### Bước 1: Trích xuất Frame & Soi Mắt Headroom 512x512
1. Xác định chính xác tài khoản: Tra cứu máy $M$, slot $Slot$, folder nguồn $F_{src} = (Slot - 1) \times 80 + M$ và folder render $F_{out}$.
2. Dùng OpenCV trích xuất frame chất lượng cao từ $F_{src}$ (hoặc $F_{out}$):
   - Bố cục chuẩn vuông `512x512`.
   - Ngũ quan nằm chính tâm, đỉnh tóc có khoảng đệm (headroom), cằm và cổ áo nằm trọn vẹn trong viền tròn xanh.
   - Kiểm định thị giác qua AI vision (`ag_cli.py ask` hoặc `browser_vision`) xác nhận sạch triệt để phụ đề, watermark, emoji, không cắt cụt cằm/đỉnh đầu.

### Bước 2: Đồng Bộ 4 Đầu Thư Mục & Đặt Khóa Bảo Vệ
1. Ghi đè file `avatar.jpg` vào cả 4 đường dẫn:
   - `D:/TIKTOK-videonuoinick/<F_out>/avatar.jpg`
   - `D:/video goc/<F_{src}>/avatar.jpg`
   - (và các alias folder tương ứng).
2. Tạo ngay marker vật lý chống bị các pipeline tự động đè lại:
   - Touch `.manual_avatar_locked` và `.manual_hashtag_locked` tại các thư mục trên.
   - Cập nhật cả 2 file registry:
     * `D:/Taadaa/data/manual_avatar_protected_folders.json`
     * `D:/Taadaa/Tiktok-video/data/manual_avatar_protected_folders.json`
3. Cập nhật SoT trong workbook:
   - Sửa đúng `Keyword Video` và `Hashtag Pool` trong `Tik<Slot>.xlsx`.
   - Đặt cột `Avatar = FORCE_UPLOAD` (hoặc `OK` sau khi nạp xong).

### Bước 3: Nạp Trực Tiếp Lên Thiết Bị Thật (Không Chờ Giục)
1. Kiểm tra máy rảnh:
   ```bash
   python D:/Taadaa/tools/inspect_machine.py <M>
   ```
   Xác nhận máy đang ở `LauncherActivity`, pin đủ, không có active lock.
2. Kích hoạt launcher nạp avatar độc lập:
   ```bash
   python D:/Taadaa/tools/run_avatar_batch_3accs.py --tik <Slot> --machine <M>
   ```
   - **Kỷ luật chạy nền (Event-Driven Wakeup):** Luôn gọi với `terminal(background=True, notify_on_complete=True, timeout=360)`.
   - Tuyệt đối CẤM viết vòng lặp sleep/polling tiến trình nền. Để harness tự đánh thức khi tiến trình nạp hoàn tất.

### Bước 4: Nghiệm Thu Thị Giác Thực Tế Trên Màn Hình App (Gate 6)
1. Khi harness báo background process completed (exit code 0):
   - Đọc kết quả trong `D:/CodexRuntime/tiktok-video/runs/run_<serial>_<timestamp>/report.json`.
   - Bắt buộc xác nhận: `"avatar_status": "FORCED_REPLACED_VERIFIED"`.
2. Kiểm chứng thị giác màn hình app thật:
   - File ảnh bằng chứng tự động lưu tại:
     `D:/CodexRuntime/tiktok-video/runs/run_<serial>_<timestamp>/avatar-uploaded-confirmed.png`
   - Dùng `ag_cli.py ask` hoặc `browser_vision` soi trực tiếp ảnh:
     * Xác nhận đúng màn hình *"Sửa hồ sơ"* của TikTok.
     * Xác nhận đúng Tên và ID tài khoản.
     * Xác nhận avatar tròn ở giữa đã cập nhật hình mới, không còn ảnh cũ lỗi dính chữ hay lệch ngách.
3. Báo cáo kết quả dứt điểm cho User kèm thẻ `MEDIA:<path_to_avatar-uploaded-confirmed.png>` và mô tả bằng chứng mắt thấy.
