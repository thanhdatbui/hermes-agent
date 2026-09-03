# Báo Cáo Kỹ Thuật: Rà Soát Toàn Diện Auto-Recovery, Khắc Phục Lỗ Hổng 5 Bước & Audit Độc Lập (20/08/2026)

## 1. Nguyên Nhân Gốc Rễ Khiến Auto-Recovery Bị "Bỏ Qua" Bước Vá Code
- **Lỗ hổng Prompt**: Trong `vision_client.py`, câu chỉ thị cũ *"Chỉ viết handler nếu chắc chắn đủ bằng chứng... ngược lại để code_patch rỗng"* khiến Gemini 3.7 Flash ưu tiên trả về `code_patch: ""` và chỉ đính kèm lệnh ADB (`keyevent 4` / `tap`).
- **Lỗ hổng `code_patcher.py`**: Khi `code_patch` rỗng, hàm trả về `no_patch_needed` $\rightarrow$ Bỏ qua hoàn toàn audit `plan-review`, chạy `pytest` và `git commit/push`.
- **Khắc phục triệt để**:
  1. Ép chặt quy tắc **CODE-FIRST** trong prompt: Mọi màn hình kẹt/lạ đều bắt buộc sinh code handler / rule xpath hoàn chỉnh vào repo trước.
  2. Bỏ dòng *"cấm tap vùng nhạy cảm"* theo chỉ đạo user.
  3. Bổ sung các rule bắt buộc: cấm factory reset, cấm `pm clear`, cấm gỡ cài đặt app.

## 2. Các Con Bug Vận Hành Đã Được Sửa & Chuẩn Hóa
1. **Quyền Hệ Thống (`PackageInstaller`)**:
   - `multi_machine_feed_session.py`: Bật mặc định `child_safety["allow_benign_popup_dismiss"] = True` để tự động tick *"Không hỏi lại"* + bấm *"TỪ CHỐI"* khi gặp hộp thoại quyền vị trí/danh bạ.
2. **Triệt tiêu False-Positive trên Feed Thường (`live_room_exit`)**:
   - Loại bỏ `@resource-id=".../long_press_layout"` khỏi rule `live_room_exit` vì đây là layout của video feed bình thường.
   - Siết chặt text nhận diện thành `"Phòng LIVE"` và `"Bảng xếp hạng hàng ngày"`.
3. **Tránh Trùng Lặp Resource ID (`ID Collision`)**:
   - Loại bỏ `e63` khỏi `learn_more_dialog_dismiss` để tránh xung đột với nút đóng Live Room.
4. **Xử Lý Zombie Process Khi Follow Hook Timeout**:
   - Trong `multi_machine_feed_session.py`: Bắt `subprocess.TimeoutExpired as exc` và gọi `exc.process.kill()` để tiêu diệt tiến trình con Python bị treo trước khi force-stop TikTok và gửi phím HOME.
5. **Chặn Alert Rác Lên Telegram Khi Chạy Pytest**:
   - Trong `alerts.py`: Kiểm tra `"PYTEST_CURRENT_TEST" in os.environ` $\rightarrow$ Return `False` ngay ở đầu hàm.
6. **Xử Lý Thoát Màn Hình Recent Apps Rỗng (`startup.py`)**:
   - Khi không tìm thấy nút *"Đóng tất cả"*, gửi lệnh `adb.keyevent(3)` (HOME) để đảm bảo đưa thiết bị về màn hình chính, tránh UI bị treo ở màn đa nhiệm.

## 3. Kết Quả Audit Độc Lập Từ 9Router Reviewer (`gpt-5.6-terra` & `gemini-3.7-flash-high`)
- Toàn bộ diff của 3 repo (`automation-core`, `tiktok-luot nuoi acc`, `tiktok-follow`) đạt điểm số **9.8/10**.
- **VERDICT: APPROVED ✅ (Ship Ready)** trên toàn bộ cụm Farm 80 thiết bị.
