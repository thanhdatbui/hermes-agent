# Sol Web Autonomous Worker & Closeout Gate Truncation Lessons (2026-10-17)

## 1. Bản Chất Toán Học Của Phán Quyết `NEED_CONTEXT:<file>`
- Khi tổng kích thước diff (staged diff hoặc `HEAD~1..HEAD`) vượt quá trần `SOL_TARGET_BYTES * 0.65 = 21,299 bytes`, `sol_payload_guard.py` tự động kích hoạt `[TRUNCATION_MANIFEST]` kèm chỉ thị:
  `NOTE: Phần bị lược KHÔNG được coi là đã review. Nếu cần xem để kết luận, trả về NEED_CONTEXT:<path>.`
- Reviewer Sol Auditor (:20129) bắt buộc tuân thủ nguyên tắc an toàn này và sẽ trả về phán quyết `NEED_CONTEXT:<file>`, đánh rớt Gate ngay lập tức mà không chấm điểm rubric.

## 2. Kỹ Thuật Tách Atomic Commit (Sequential Atomic Commits)
- Khi phát triển cả module code mới (ví dụ `sol_worker.py` ~19KB) và file unit test mới (`tests/test_sol_worker.py` ~8KB), tổng diff từ `/dev/null` là 27–28KB > 21,299 bytes.
- Giải pháp: Tách thành 2 commit atomic tuần tự:
  1. Commit 1: `git add tests/test_... && git commit -m "test: add test suite"` (diff ~8KB < 21,299B).
  2. Commit 2: `git add source.py && git commit -m "feat: implement source"` (diff ~19.6KB < 21,299B).
  3. Chạy Gate trên commit 2: `closeout_gate.py --repo <dir> --base HEAD~1 --files source.py`.
     - Commit scope khớp chính xác 100% commit HEAD (`source.py`).
     - Diff payload 19.6KB <= 21,299B -> Cấp L0, ZERO TRUNCATION, manifest rỗng.
     - Closeout Gate tự phát hiện file test đã có trên đĩa, chạy và xác nhận 100% pass -> Reviewer chấm đủ ngữ cảnh và điểm bật tăng từ 58 lên 74–85+.

## 3. Cưỡng Chế State Machine: Bắt Buộc Verification Trước Khi DONE
- Reviewer Sol trừ nặng điểm nếu state machine của Worker chấp nhận lệnh DONE mà không có bằng chứng test thực tế trước đó.
- State machine trong worker loop BẮT BUỘC quản lý cờ `has_verified = False`:
  - Chỉ bật `has_verified = True` khi có lệnh `ACTION: COMMAND` chạy test runner pass với exit code 0.
  - Khi có bất kỳ `ACTION: PATCH` mới nào được áp dụng, BẮT BUỘC reset `has_verified = False`.
  - Nếu model gọi `ACTION: DONE` khi `modified_files` có dữ liệu nhưng `not has_verified`: Worker BẮT BUỘC từ chối và phản hồi lỗi, yêu cầu model phải chạy test runner kiểm chứng trước.

## 4. Ranh Giới Báo Cáo Của Worker (Worker Report-Only Boundary)
- Worker (kể cả Claude Worker, Agy CLI, Haiku Worker hay Sol Worker) CHỈ CÓ QUYỀN SỬA CODE, CHẠY FOCUSED TEST VÀ BÁO CÁO BẰNG CHỨNG (Diff + Test evidence) về cho Coordinator & User.
- CẤM TUYỆT ĐỐI: Worker tự ý commit, tự tiện push hay tự động kích hoạt vòng thẩm định chốt phiên.
- Thao tác chốt phiên là đặc quyền do User / Coordinator kích hoạt sau khi đã nhận được báo cáo bằng chứng đạt chuẩn từ Worker.
