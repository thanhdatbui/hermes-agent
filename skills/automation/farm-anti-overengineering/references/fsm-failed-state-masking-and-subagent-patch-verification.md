# FSM State Masking, Zero-Delay Worker Dispatch & Subagent Patch Verification (Máy 74 - 06/09/2026)

## 1. Bối cảnh & Giám sát từ User
- Khi có Farm Alert, user liên tục theo dõi và kiểm tra tính tuân thủ của Coordinator: *"nãy gọi delegate hay tự làm"*.
- **Kỷ luật tuyệt đối:** 100% các bước điều tra sâu (đọc log `runs/`, phân tích flow), sửa code codebase, viết focused test và chạy Canary đều BẮT BUỘC dispatch worker subagent qua `delegate_task`. Coordinator ở session chính CHỈ inspect hiện trường O(1), gán proxy/wifi khi rớt mạng, và chụp screencap gửi proof.

## 2. Cạm bẫy FSM State Masking (`failed_at_state_FAILED`)
- Khi state machine gặp lỗi tại bất kỳ state nào (`CAPTION_FILL`), hàm `_transition(False)` gán `self.current_state = fail_state` (`WorkflowState.FAILED`).
- Reporter ghi `machine.current_state.value` vào `report.json` $\rightarrow$ `last_state: "FAILED"`.
- Hệ thống watchdog/alert đọc `last_state` và sinh mã lỗi `failed_at_state_FAILED`, làm lu mờ hoàn toàn state thực sự bị lỗi (`CAPTION_FILL`).
- **Giải pháp:** Bắt buộc lưu `last_failed_state = self.current_state` trước khi đổi state sang `FAILED`, đồng thời lưu `failed_state_val` vào `report.json`.

## 3. Cạm bẫy Worker Subagent Self-Report (Báo đã patch nhưng chưa ghi đĩa)
- Worker subagent có thể chạy xong và báo cáo *"Đã áp dụng Patch Contract thành công"*, nhưng thực tế do tool call phân trang hoặc race condition, byte code chưa hề được lưu vào file vật lý.
- **Quy tắc bắt buộc cho Coordinator:**
  - CẤM tin tưởng mù quáng summary text của worker.
  - Ngay trước Gate 1 Review và Gate 2 Commit, Coordinator BẮT BUỘC kiểm tra `git status --short` và `git diff` (hoặc `git diff remotes/origin/<branch> HEAD`) để xác nhận trực tiếp các dòng diff vật lý trên đĩa.
  - Nếu phát hiện phần code chưa được áp dụng, áp dụng ngay trước khi kích hoạt Review.

## 4. Floating Text Selection Menu & Non-Fatal Draft Cleanup
- **Floating Toolbar:** Trên Samsung Android, khi paste hoặc nhập caption, text bị select all sẽ kích hoạt popup nổi ("CẮT | CHÉP | DÁN | BỘ NHỚ TẠM") che mất ô nhập và nút Đăng. Xử lý bằng cách nhận diện các nhãn này trong XML dump sau settle và gửi phím cứng `KEYCODE_BACK`.
- **Non-Fatal Auxiliary Cleanup:** Thao tác dọn dẹp bản nháp cũ (`_delete_all_profile_drafts`) chỉ là dọn rác phụ trợ. Nếu không tìm thấy nút chọn tất cả, chỉ ghi warning log, bấm Back về hồ sơ và tiếp tục upload video, tuyệt đối không gán `is_ui_unavailable = True` làm dừng toàn bộ quy trình upload.
