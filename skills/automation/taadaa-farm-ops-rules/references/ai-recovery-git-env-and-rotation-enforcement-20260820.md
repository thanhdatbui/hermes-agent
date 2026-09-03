# Báo Cáo Kỹ Thuật & Bài Học Vận Hành: AI Auto-Recovery Git/Env Fix & Khóa Cứng Xoay Dọc Toàn Farm (20/08/2026)

---

## 1. Nguyên Nhân Gốc Rễ Khiến AI Auto-Recovery "Commit Thất Bại Hoài" & Cách Khắc Phục

Trong quá trình vận hành, AI Auto-Recovery agent liên tục báo:
`⚠️ Patch áp dụng nhưng commit thất bại — pytest_failed_rolled_back` hoặc `git_failed: [WinError 2] The system cannot find the file specified`.

### Ba Điểm Nghẽn Kỹ Thuật Cốt Lõi:
1. **Xung đột Môi Trường Python & Thư viện Pillow**:
   - Agent chạy dưới quyền tiến trình con được spawn từ Hermes (`sys.executable` = Hermes venv), nhưng `code_patcher.py` lại chạy `pytest` bằng chính `sys.executable` đó kèm `PYTHONPATH` của Hermes.
   - Gây lỗi `ImportError: cannot import name '_imaging' from 'PIL'` ngay khâu pytest collection $\rightarrow$ pytest luôn fail $\rightarrow$ code_patcher rollback code về ban đầu.
   - **Khắc phục**: Khóa cứng `_AUTOMATION_PYTHON = D:\Taadaa\python-envs\automation\Scripts\python.exe` và chủ động xóa `PYTHONPATH` trong `_AUTOMATION_ENV`.

2. **Lỗi `WinError 2` khi gọi Git trong Subprocess Chạy Nền**:
   - Khi chạy ngầm, biến môi trường `PATH` của subprocess không chứa đường dẫn tới `git` $\rightarrow$ `subprocess.run(["git", ...])` crash với `WinError 2`.
   - **Khắc phục**: Khai báo đường dẫn tuyệt đối cho `_GIT_EXE = r"C:\Program Files\Git\cmd\git.EXE"` (fallback `C:\Program Files\Git\mingw64\bin\git.EXE`).

3. **3 Test Pre-existing Fail trong `test_benign_popup.py`**:
   - Fixture `PACKAGEINSTALLER_LOCATION_XML` thiếu thuộc tính `checkable="true" checked="false"` và mock `capture_calibration_attempt` thiếu lần capture thứ 2 để verify checkbox "Không hỏi lại" đã được tick $\rightarrow$ 2 test location luôn fail.
   - Test `test_sponsored_learn_more_overlay` assert `popup_type` trong khi cơ chế mới đã chuyển sang swipe-first.
   - **Khắc phục**: Sửa mock test theo đúng pattern test contacts đang PASS (tick checkbox 545,1080 $\rightarrow$ tap TỪ CHỐI 557,1200), không sửa logic an toàn core.

4. **Hiện Tượng AI Tự Sinh Code Lỗi (Dead-code & API Ảo)**:
   - Gemini sinh code append vào cuối `benign_popup.py` gọi các hàm không tồn tại trên `DeviceContext` (`ctx.dump_ui_state()`, `ctx.tap()`, `ctx.screen_size`, `ctx.send_keyevent()`).
   - Các hàm này nằm chết ở cuối file và không được nối vào mạch gọi `dismiss_allowed_generic_popup`.
   - **Khắc phục**: Dọn sạch dead-code và chuẩn hóa thành `GemPhoneFarmBlindPopupRule` chính quy trong `feed_swipe_smoke.py`.

---

## 2. Danh Mục Các Popup Được Chuẩn Hóa Canonical (20/08)
- **MÁY 35**: Bottom banner quảng cáo Closeup / *"Được đề xuất cho bạn / Mở trang web"* $\rightarrow$ Rule `recommendation_or_brand_profile_back` (gửi phím `BACK`).
- **MÁY 41**: Widget thưởng nổi *"Nhấp ngay có thưởng"* trên feed $\rightarrow$ Rule `floating_reward_badge_close` (tap nút `close_btn` / `(x)`).
- **MÁY 48**: Popup xin quyền danh bạ *"Để kết nối với những người bạn biết..."* $\rightarrow$ Rule `contact_permission_dialog_deny` (tap *"Không cho phép"*).
- **MÁY 63 & MÁY 40**: Khung soạn thảo comment / Bàn phím ảo mở đè video feed $\rightarrow$ Rule `comment_input_overlay_back` (gửi phím `BACK` để hạ bàn phím và đóng ô comment).

---

## 3. Khóa Cứng Xoay Dọc Màn Hình (0 Độ Portrait) Toàn Farm
- **Hiện tượng Máy 41**: Máy bị bật chế độ tự động xoay (`accelerometer_rotation = 1`) $\rightarrow$ Khi lướt trúng video ngang, hệ điều hành Samsung tự xoay ngang màn hình làm lệch tọa độ vuốt.
- **Xử lý toàn diện**:
  1. Quét toàn bộ 80 máy, gửi lệnh ADB khóa kép (Dual-layer lock: `settings put` + `content insert` vào Settings Content Provider) ép `accelerometer_rotation = 0` và `user_rotation = 0`.
  2. Nhúng trực tiếp `lock_portrait_rotation(ctx)` vào ngay đầu hàm `_feed_session_flow` trong `feed_swipe_smoke.py` $\rightarrow$ Mọi phiên lướt nuôi đều tự động ép dọc 0 độ trước khi swipe.
