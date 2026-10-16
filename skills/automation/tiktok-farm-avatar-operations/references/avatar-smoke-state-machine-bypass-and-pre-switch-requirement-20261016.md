# Avatar Smoke State Machine Bypass & Pre-Switch Requirement on Multi-Account Farm (2026-10-16)

## 1. Căn Nguyên Kiến Trúc: State Machine Bypass trong `avatar_smoke`

### 1.1. Hiện tượng & Vấn đề Cốt lõi
- Khi chạy đổi avatar bằng launcher độc quyền `run_tiktok_upload_avatar.ps1` hoặc `run_tiktok_upload_batch.ps1 -AvatarOnly`:
  Trạng thái thực thi được truyền cờ `--avatar-smoke`.
- Trong `D:\Taadaa\Tiktok-video\scripts\tiktok_workflow\state_machine.py`, chuyển trạng thái có đoạn logic:
  ```python
  if (
      self.current_state == WorkflowState.RESOLVE_DEVICE
      and self.context.config.get("avatar_smoke") is True
  ):
      self.current_state = WorkflowState.ENSURE_AVATAR
  ```
- **Hậu quả:** Runner nhảy tắt từ `RESOLVE_DEVICE` thẳng vào `ENSURE_AVATAR`, **hoàn toàn bỏ qua trạng thái `ACCOUNT_SWITCHER`** (vốn diễn ra tại State #9).
- Trên farm Taadaa, mỗi thiết bị quản lý tới 8 tài khoản (Tik 1 đến Tik 8). Nếu thiết bị đang mở sẵn một tài khoản khác (ví dụ Tik 8 `@thutuan4916` đang active trên app TikTok, nhưng nhiệm vụ yêu cầu đổi avatar cho Tik 4 `@vantieu11`), runner sẽ mở tab Hồ sơ -> Sửa hồ sơ và **upload đè avatar lên tài khoản đang mở sẵn**, gây lỗi đột biến nhầm nick nghiêm trọng (False Target Avatar Mutation).

---

## 2. Quy Tắc Pre-Switch Bắt Buộc Trước Avatar Flow

Trước khi thực thi thay đổi avatar (kể cả qua runner hay direct adb script):

1. **Kiểm tra Identity của Tài khoản Active:**
   - Dump UI XML của màn hình Hồ sơ hiện tại.
   - Kiểm tra xem handle `@target_username` có xuất hiện trong danh sách nodes (`text` hoặc `content-desc`) hay không.
   - Nếu handle active trùng khớp: Tiếp tục quy trình Sửa hồ sơ.
   - Nếu handle active khác nick mục tiêu: **BẮT BUỘC mở Account Switcher để chuyển nick trước.**

2. **Tọa độ Mở Switcher trên TikTok v47 Layout C (Bong bóng Note):**
   - Trên Layout C (Avatar góc trên-phải `[708,300][1080,636]` kèm bong bóng Note "Thì thầm to nhỏ" / "Tám chuyện nào"):
     Header trên cùng không có icon dropdown truyền thống.
   - **Nút mở Switcher thực tế:** Là Button chứa Tên hiển thị (Display Name) nằm ở góc trên-trái:
     - `bounds`: `[36, 280][567, 364]` (hoặc `[36, 280][444, 364]`).
     - Tọa độ tap an toàn: `(300, 320)` (hoặc tâm của button chứa Display Name).
   - Tapping vào button này sẽ kích hoạt bottom sheet danh sách tài khoản.

3. **Chọn Nick & Chờ Đồng Bộ:**
   - Quét danh sách tài khoản trong switcher (`target_user in node.text`).
   - Nếu chưa thấy (do nằm ở dưới danh sách): vuốt nhẹ `input swipe 540 1400 540 800 300` và dump lại.
   - Tap vào tâm node của tài khoản mục tiêu.
   - Nghỉ 4–5 giây để TikTok nạp profile mới, sau đó dump UI xác nhận handle `@target_username` đã active.

---

## 3. Dấu Hiệu Màn Hình Ngủ (Black Screencap 12,491 Bytes)

- **Đặc trưng:** Khi thiết bị Samsung S7 (G930F/K/S) đang ở trạng thái ngủ màn hình (Screen OFF/Sleep), lệnh `screencap -p` xuất ra file PNG có kích thước cố định khoảng **12,491 bytes** (ảnh đen tuyền).
- **Quy tắc an toàn:**
  - Luôn gửi lệnh đánh thức trước khi thao tác: `input keyevent 224` (KEYCODE_WAKEUP) và `input keyevent 82` (UNLOCK).
  - CẤM TUYỆT ĐỐI gửi ảnh nghiệm thu có dung lượng ~12.5KB hoặc toàn màu đen cho User (vi phạm Invariant LLM Soi Mắt Đọc Ảnh).

---

## 4. Kỷ Luật Phân Vai Coordinator T1 & Worker Gate Delegation

1. **Hạn Ngạch T1 Coordinator:**
   - Coordinator bị trần cứng T1: tối đa 5 files, <= 200 dòng code mới cộng dồn cả session.
   - Khi hết ngân sách T1, hệ thống từ chối `write_file` và yêu cầu dispatch Worker qua `delegate_task`.
2. **Quy Định Soạn Contract `delegate_task`:**
   - `FILE: D:\Taadaa\tmp\<script_name>.py` nằm trên một dòng riêng biệt có dấu xuống dòng.
   - `FOCUSED_TEST: python -m py_compile D:\Taadaa\tmp\<script_name>.py` nằm trên dòng riêng biệt.
   - `FAIL_FAST:` Cảnh báo Worker dừng ngay nếu scope vượt quá ngân sách trong 3 lượt đầu.
   - Worker subagent bị hạn chế terminal (chỉ được chạy git, adb devices, inspect_machine, pytest, psutil; không được chạy script Python tùy ý ngoài whitelist). Do đó, Worker chỉ viết/sửa code và kiểm tra py_compile; Coordinator nhận kết quả và kích hoạt chạy qua `terminal(background=True)` hoặc `operator_device_lock`.
