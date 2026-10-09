# Bẫy Kẹt Mở Tab Anchor (Mode 2) & Quy Chuẩn Farm Alert Khi Lỗi Script Hook Hàng Loạt (25/09/2026)

## 1. Hiện Tượng & Nguyên Nhân Kẹt Mở Tab Anchor (Mode 2 -> Bỏ Rơi Mode 1 Bù Lượt)
- **Vấn đề thực tế**: Toàn bộ farm có ngân sách 10-20 follow/phiên nhưng mỗi ca chỉ tăng lẹt đẹt +1 hoặc +2 following.
- **Nguyên nhân cốt lõi trong `mode2_follow_followers.py`**:
  1. Khi follow nick Anchor thành công (+1), runner mở tab "Đang follow" của Anchor để lấy danh sách follow tiếp các nick farm khác.
  2. Nếu mở tab thất bại lần 2 (do lag mạng/selector), code cũ gán `res.status = "MANUAL_REVIEW"`, `res.failed = True` và gọi lệnh `break` thoát khỏi toàn bộ session.
  3. Lệnh `break` này chặn đứng không cho thử Anchor tiếp theo, đồng thời khiến `follow_engine.py` thấy `status != OK` nên **HỦY BỎ LUÔN MODE 1 (SEARCH FOLLOW BÙ)**.
  4. Hậu quả: Nick chỉ kịp follow đúng 1 lượt Anchor (+1) rồi kết thúc ca nuôi.
- **Khắc phục chuẩn**:
  - Khi mở tab Anchor thất bại lần 2: ghi `logger.warning(...)` và `continue` để safe-skip sang Anchor tiếp theo.
  - Kết thúc Mode 2 trong trạng thái `res.status = "OK"` để `follow_engine.py` tự động kích hoạt **Mode 1 (Search Follow)** bù đủ số lượng follow còn thiếu trong ngân sách.

## 2. Quy Chuẩn Bắn Farm Alert Khi Lỗi Script Hook Hàng Loạt (Cả Follow & Upload Video)
- **Bẫy lọt lưới cũ**:
  - `batch_aggregator.py` chỉ đọc `final_status` của bước lướt feed trong `run_manifest.json`, hoàn toàn bỏ qua `follow_result.json` và `upload_result.json`. Máy lướt feed xong nhưng follow/upload lỗi hàng loạt vẫn bị coi là 100% thành công, 0 Farm Alert nào được phát ra.
  - `feed_session_watchdog.py` chỉ in số máy cộc lốc `+ Lỗi script/xác minh: 32, 48`, không nêu rõ nguyên nhân.
- **Quy chuẩn đồng bộ 2 tầng**:
  1. **Tầng Batch Aggregator (`automation-core`)**:
     - `_parse_multi_machine_summary` tự động đọc `follow_result.json` và `upload_result.json` trong thư mục artifact của từng máy.
     - Phát hiện mọi lỗi: `MANUAL_REVIEW`, `FOLLOW_FAILED`, `exit_code != 0`, `timeout`, `error` (loại trừ các trường hợp skip hợp lệ như dưỡng sinh, chưa đủ video, đã upload...).
     - Phân loại rõ ràng: `FollowScriptError`, `FollowReleasedError`, `UploadScriptError`.
     - Kích hoạt `🚨 [BATCH ALERT: LỖI HỆ THỐNG]` khi có $\ge 3$ máy (hoặc $\ge 10\%$) dính lỗi.
  2. **Tầng Watchdog Telegram (`feed_session_watchdog.py`)**:
     - Tự động giật tiêu đề đỏ `🚨 [FARM ALERT] PHÁT HIỆN LỖI SCRIPT HÀNG LOẠT (X máy lỗi script Follow) - Ca X (Row Y)` khi $\ge 3$ máy dính lỗi.
     - Gom nhóm lý do lỗi chi tiết theo nguyên nhân (ví dụ: `Kẹt mở tab Đã follow sau ladder (2: M32, M48)`).

## 3. Quy Chuẩn Kỷ Luật Chốt Phiên (Session Close Discipline)
- Khi User ra lệnh "Chốt / Chốt phiên / Wrap up" và Reviewer độc lập đã chấm `Verdict: APPROVED` (Score >= 85):
  - Agent **BẮT BUỘC PHẢI THỰC HIỆN `git add` + `git commit` + `git push`** để hoàn tất chốt phiên.
  - Tuyệt đối CẤM hiểu sai quy định an toàn thành việc "dừng lại ở trạng thái modified rồi báo không tự ý commit/push". Lệnh cấm chỉ áp dụng khi CHƯA QUA reviewer closeout gate.
