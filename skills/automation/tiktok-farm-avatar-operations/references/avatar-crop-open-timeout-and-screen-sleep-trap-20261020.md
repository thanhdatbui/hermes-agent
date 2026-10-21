# Bẫy Màn Crop Avatar Không Mở (AVATAR_CROP_OPEN_FAILED), Màn Hình Ngủ & Kỷ Luật Không Hứa Lèo (2026-10-20)

## 1. Bẫy Kỹ Thuật: AVATAR_CROP_OPEN_FAILED & Màn Hình S7 Bị Ngủ Giữa Flow

### Hiện tượng & Triệu chứng
- Runner nạp avatar (`run_upload_avatar.py` / `run_tiktok_upload_avatar.ps1`) chạy đến bước chọn ảnh trong Photo Picker:
  `[ENSURE_AVATAR] Tap tile ảnh đầu tiên (mới nhất sau push): (6, 222, 269, 488)`
  `[ENSURE_AVATAR] Selection screen remained; tapping visible Next button`
- Sau đó văng exception và dừng lại:
  `[AVATAR_CROP_OPEN_FAILED] ENSURE_AVATAR: Màn crop avatar không mở`
- Các file ảnh hiện trường sinh ra trong `runs/run_<serial>_<timestamp>/`:
  * `avatar-crop-open-failed.png`
  * `avatar-crop-open-visual-*.png`
  Tất cả đều có dung lượng nhỏ (~12 KB) và **đen hoàn toàn** (`mean: 0.0`, toàn bộ pixel `(0, 0, 0)`).

### Gốc rễ kỹ thuật
1. **Deadline ngắn (25s) vs dump_ui chậm trên Galaxy S7:**
   - Trong `state_machine.py` hàm `_save_avatar_without_story`, vòng lặp kiểm tra màn crop có giới hạn cứng:
     `deadline = time.time() + 25.0`
   - Trên các máy Samsung Galaxy S7 (SM-G930F) cũ hoặc sau khi vừa chạy ca nuôi nick dài (ATX agent bị lag / uiautomator restart), mỗi lần gọi `adapter.dump_ui()` mất từ 8 đến 12 giây.
   - Khi bấm nút "Tiếp (1)", app TikTok mất vài giây để chuyển activity sang màn Crop. Hai lần `dump_ui` chậm đã ngốn hết 25 giây của deadline, khiến vòng lặp thoát trước khi nhận diện được màn Crop.
2. **Màn hình tự tắt (Screen Sleep / Dozing) do timeout hệ thống:**
   - Khi `dump_ui` bị treo hoặc kéo dài quá 15-30 giây mà không có thao tác cảm ứng (touch event), màn hình S7 tự động rơi vào trạng thái `Sleep/Dozing`.
   - Khi màn hình đã tắt:
     * Lệnh `adb exec-out screencap -p` xuất ra framebuffer rỗng màu đen (`mean = 0.0`).
     * Các lệnh tap tọa độ không ăn vào giao diện app.
     * Cả nhận diện UI XML lẫn nhận diện thị giác (visual classifier) đều thất bại vì màn hình tối om.

### Khắc phục & Điều phối
- Kiểm tra trạng thái hiện trường bằng `python D:/Taadaa/tools/inspect_machine.py <N>`.
- Nếu thấy `Màn hình: OFF (Sleep/Dozing)` và `Current Focus` đã văng về `LauncherActivity`:
  * Runner đã tự động dọn dẹp và trả device lease.
  * Máy đã hạ nhiệt và trống tiến trình: **Kích hoạt chạy lại ngay runner nạp lần 2** qua background process. Khi khởi động lại, runner sẽ tự đánh thức màn hình (`wake_unlock_read_state`) và thực thi lại từ đầu.

---

## 2. Kỷ Luật Vận Hành: Tuyệt Đối Cấm "Hứa Lèo" / Nói Suông Không Kèm Action

### Nguyên tắc 0-Empty-Promise Turn
- Khi Operator bức xúc chất vấn về tiến độ ("Sao mãi đéo up được", "Bị clg từ tối đến giờ"):
  * **CẤM TUYỆT ĐỐI**: Trả lời trần thuật dài dòng rồi chốt câu *"Em chạy lại runner ngay bây giờ"* nhưng **KHÔNG HỀ GỌI TOOL CHẠY TIẾN TRÌNH** trong cùng lượt đó.
  * Hành vi hứa sẽ làm mà không làm ngay lập tức khiến Operator ức chế tột độ.
- **Hành động bắt buộc**:
  * Nếu nói sẽ chạy lại: BẮT BUỘC gọi ngay tool `terminal(command="python D:/Taadaa/tools/run_upload_avatar.py ...", background=True, notify_on_complete=True)` NGAY TRONG TURN ĐÓ.
  * Tin nhắn gửi Operator phải trả về `pid` hoặc `session_id` của tiến trình nền đang thực sự chạy, chứng minh hành động cụ thể đã được kích hoạt.
