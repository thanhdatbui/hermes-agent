# Quy Tắc Vận Hành Dưỡng Sinh & Đăng Video (Chốt 2026-10-11)

## 1. Bỏ Tỷ Lệ Dưỡng Sinh Tự Nhiên Ngẫu Nhiên (Organic Rest Ratio = Disabled)
- **Bối cảnh & Quyết định:**
  - Trước đây, `_is_account_organic_rest_day` áp dụng băm MD5 `(date:machine:row) % 3 == 0` để gán ngẫu nhiên 33% số nick vào "Ngày Dưỡng Sinh".
  - Khi dính cờ này, nick bị chặn cả follow (`organic-rest-day-pure-feed`) lẫn upload (`organic-rest-day-upload-disabled`), dẫn đến nhiều máy bị bỏ qua không đăng video dù kho video và tài nguyên đều sẵn sàng.
  - **Quy tắc mới (Chốt 2026-10-11):** BỎ HOÀN TOÀN tỷ lệ nghỉ ngẫu nhiên 1/3 này. Hàm `_is_account_organic_rest_day` mặc định luôn trả về `False`.
- **Ngoại lệ duy nhất:**
  - Trạng thái `organic_rest` CHỈ được phép kích hoạt khi nick được chỉ định đích danh trong sổ cái can thiệp `force_rest_ledger` (ví dụ nick dính án phạt nặng, 0-view kéo dài cần ngâm feed xả tải).

## 2. Cờ Upload Mở Ở Cả 2 Phiên (-AllowUploadHook)
- **Quy tắc điều phối runner:**
  - Cờ `-AllowUploadHook` trong `tiktok_runner.py` BẮT BUỘC mở ở CẢ 2 phiên (Phiên 1 và Phiên 2) trong mỗi ca chạy.
  - **Cơ chế chống đăng trùng:** Sổ cái `shift_upload_history.json` tự động ghi nhận phiên đăng thành công. Nếu Phiên 1 (06h) đã upload thành công thì Phiên 2 (08h) tự động skip an toàn.
  - Invariant: CẤM chặn upload ngày nghỉ; nếu nick có lịch chạy và có video sẵn sàng thì luôn được đăng 1 video/ngày.

## 3. Quy Trình Điều Phối Worker Cho Monolith (Học Được Từ Phiên 2026-10-11)
- Khi dispatch Worker sửa code monolith lớn (`multi_machine_feed_session.py` ~6000 dòng):
  - CẤM Worker gọi `search_files` hoặc `grep` vì sẽ bị Worker Guard chặn (`GUARD_SEARCH_FILES_ROOT` / `TOOL DEFAULT-DENY`).
  - Coordinator phải tự grep O(1), xác định chính xác số dòng và anchor duy nhất `c == 1`, sau đó yêu cầu Worker gọi `patch(mode='replace')` ngay ở iteration 1.
  - Khi gặp Strike 3 tại `closeout_gate.py` (`[REVIEWER_HANDOFF_TRIGGERED: 3 consecutive rejections]`), Coordinator BẮT BUỘC dừng tự sửa và chuyển giao quyền cho Claude CLI (Sonnet 3.5) với vai trò Reviewer-with-write-access theo đúng `HERMES_SUBAGENT_RULES.md`.
