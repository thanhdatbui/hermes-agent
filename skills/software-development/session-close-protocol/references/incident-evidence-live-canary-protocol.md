# Incident Evidence Live Canary & Release Protocol

## 1. Trigger & Scope
Khi phiên bắt đầu hoặc trong quá trình làm việc có **incident evidence** (ảnh chụp màn hình lỗi, screenshot hiện trường, alert log từ máy farm cụ thể):
- **CẤM gán `CANARY_NOT_APPLICABLE`** dù code sửa ở consumer repo hay ở shared core (`automation-core`).
- Bắt buộc resolve machine ID $\rightarrow$ serial qua workbook canonical (`Tik1.xlsx`, `Tik2.xlsx`, `taikhoan_run_safe.xlsx`).

## 2. Quy trình Live Canary hoàn chỉnh trên máy thật
Một lần Live Canary hợp lệ khi fix popup/lỗi runtime KHÔNG ĐƯỢC dừng lại ở việc tap nút thủ công, mà phải chạy qua chuỗi runner chuẩn:
1. **Pre-dismiss check:** Dump XML / screencap để đối soát detector nhận diện đúng popup và đúng nút hành động (ví dụ `dismiss_deny_button` trỏ vào `"Không cho phép"`).
2. **Runner Execution:** Chạy runner chế độ test có giới hạn:
   - Với feed session: Chạy `feed-swipe-smoke` (hoặc `feed-session-smoke`) với `--max-swipes 2` (hoặc `--recovery-test-swipes 2`), `--allow-feed-swipe`, `--allow-navigation-only`, `--allow-benign-popup-dismiss`, `--cleanup-on-stop`.
   - Đảm bảo runner tự động xử lý popup, lướt đủ số lượt swipe thử nghiệm, và tự động gọi cleanup đưa màn hình về Home.
3. **Post-dismiss & Unlock Verification:**
   - Hậu kiểm screencap xác nhận popup đã biến mất, app đã về Home / feed sạch.
   - Kiểm tra thư mục `~/.codex/device-locks/` đảm bảo file lock của serial máy đích đã được giải phóng hoàn toàn (`released` / không còn file lock tồn tại).
   - Đính kèm đường dẫn ảnh `MEDIA:<path>` trong báo cáo kết quả.

## 3. Chained Workflow Canary Gate (Nuôi Feed -> Upload Hook / Follow)
Khi Canary kích hoạt luồng chuỗi (ví dụ Phiên 3 feed gọi Upload Hook `scripts.tiktok_workflow` hoặc Follow runner):
- **CẤM** coi việc parent process (feed runner) kết thúc hoặc kích hoạt hook là Canary PASS.
- BẮT BUỘC kiểm tra artifact kết quả cuối của child runner:
  - `upload_result.json`: `status == "success"`, `exit_code == 0`, `reason == ""` (hoặc không có lỗi subprocess).
  - `report.json`: `status == "DONE"` / `post_verified == true`.
- Nếu child runner trả về `status: "failed"`, `exit_code != 0`, hoặc màn hình thiết bị còn kẹt ở composer/post surface (chưa bấm Đăng hoặc kẹt caption/keyboard), Gate 0 BẮT BUỘC BỊ ĐÁNH DẤU `FAIL`/`BLOCKED_AT_GATE_0`.
- **TUYỆT ĐỐI CẤM** tự ý xóa file lock `~/.codex/device-locks/machine_*.lock.json` bằng tay và cấm báo cáo sai sự thật ("báo xong láo") khi child runner chưa hoàn thành trọn vẹn task.
