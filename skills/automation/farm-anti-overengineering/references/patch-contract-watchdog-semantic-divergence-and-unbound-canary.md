# Patch Contract Execution: Watchdog Semantic Divergence & Lean Canary Lessons (06/09/2026)

## 1. Bối cảnh
Áp dụng Patch Contract trên `multi_machine_feed_session.py` (ngân sách <= 8 tool calls) nhằm loại bỏ race condition giữa worker lease release và watchdog deadline preemption:
- **Patch 1 (`_claim_watchdog_terminal`):** Thêm điều kiện `timing.get("success_release_started")` để chặn watchdog claim khi worker đã bắt đầu quá trình nhả lease thành công.
- **Patch 2 (`_release_under_lock`):** Đơn giản hoá `_record_completion()` để ghi nhận hoàn tất release vô điều kiện mà không kiểm tra lại deadline mono hay `publication_owner`.

## 2. Các cạm bẫy & Bài học thực chiến

### Cạm bẫy 1: `search_files` IO error (os error 3) trên đường dẫn Windows ổ D
- **Hiện tượng:** Dùng `search_files(path=r'D:\Taadaa\tiktok-luot nuoi acc\...')` bị ripgrep báo:
  `Search failed: rg: /d/Taadaa/tiktok-luot nuoi acc/...: The system cannot find the path specified. (os error 3)`
- **Xử lý chuẩn:** Tránh dùng `search_files` trên đường dẫn dài có dấu cách/tiếng Việt. Dùng `read_file` trực tiếp với path đầy đủ hoặc dùng terminal `grep -n` trên file đích cụ thể.

### Cạm bẫy 2: Test Suite Semantic Divergence (Test cũ fail do thay đổi ngữ nghĩa có chủ đích)
- **Hiện tượng:** Chạy `pytest ... -k "watchdog"` bị fail đúng 1 test:
  `FollowReleaseAndWarmupClassificationTests::test_watchdog_interleaving_with_success_release`
- **Nguyên nhân gốc rễ:** Test cũ được viết để assert mô hình cũ (watchdog được phép giật quyền terminalize nếu deadline chạm đáy trong khi worker đang release). Khi Patch Contract đổi sang mô hình mới (bảo vệ quyền nhả lease của worker ngay từ `success_release_started`), assertion cũ `self.assertTrue(_claim_watchdog_terminal(timing))` chắc chắn fail.
- **Kỷ luật Worker:** 
  - **CẤM** tự ý sửa file test khi chưa được giao quyền (giữ vững Scope Lock).
  - **CẤM** rơi vào vòng lặp điều tra/debug test khi thay đổi này nằm trong thiết kế của patch contract.
  - Ghi nhận chính xác nguyên nhân test fail, hoàn tất canary và báo cáo rõ cho Coordinator xử lý cập nhật test trong phase closeout.

### Cạm bẫy 3: UnboundLocalError `recaptured_xml` trong Canary Máy 36
- **Hiện tượng:** Canary máy 36 dừng với lỗi:
  `[ALERT] [MÁY 36] Dừng: failed | Lý do: cannot access local variable 'recaptured_xml' where it is not associated with a value`
- **Nguyên nhân:** Biến `recaptured_xml` trong flow UI/re-capture được tham chiếu trước khi được gán (unbound local) ở một nhánh rẽ ngoại lệ hoặc recovery.
- **Kỷ luật:** Báo cáo artifact directory (`.ai-runs/<timestamp>/`) và lý do dừng máy để Coordinator mở task sửa độc lập.
