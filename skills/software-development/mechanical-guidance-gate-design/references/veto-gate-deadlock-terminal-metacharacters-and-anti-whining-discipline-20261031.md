# Veto Gate Deadlock vs Actionable Guidance: Terminal Metacharacters vs Pytest Compulsion

## 1. Bản Chất Bẫy Bại Liệt (Deadlock / Catch-22)
* **Luật Compulsion (Bắt buộc kiểm chứng):** Worker sau khi sửa code bắt buộc phải chạy lệnh test focused (`pytest` hoặc `python -m pytest`) có exit code = 0 thì mới được phép phát hành `ACTION: DONE`.
* **Luật Veto Guard (Chặn mù quáng):** Bộ lọc `is_command_safe` trong sandbox (`sol_worker.py` / `gemini_web_worker.py`) dùng regex chặn shell metacharacters `[;&|`$<>]`. Khi Worker chạy lệnh test có chứa quote, newline, flags phức tạp hoặc command parsing thô, Guard từ chối với thông báo:
  `Command contains dangerous shell metacharacters`
* **Vòng lặp tê liệt:**
  1. Worker muốn DONE ➔ Phải chạy pytest.
  2. Worker gọi pytest ➔ Bị Guard Veto chặn họng vì hiểu nhầm là shell injection.
  3. Worker thử lại các biến thể (`pytest`, `py.test`, `python -m pytest`) ➔ Đều bị chặn ➔ Cháy sạch 12 turns ➔ Văng `ACTION: BLOCKED`.
  4. Coordinator nhận kết quả thất bại ➔ Thử can thiệp nhưng đụng trần ngân sách sửa code T1 (<= 500 dòng) ➔ Coordinator dừng lại phân trần miệng.
  5. Receipt Guard ở gateway phát hiện phát ngôn khẳng định nhưng không có task_id / receipt thành công ➔ Đóng dấu đỏ:
     `⚠️ [HỆ THỐNG CẢNH BÁO — CHƯA CÓ WORKER NÀO CHẠY THẬT]`.
  6. Agent rơi vào phản xạ phòng thủ (khóc lóc / xin lỗi / liệt kê lý do) thay vì tìm action tiếp theo.

## 2. Kỷ Luật Phản Ứng Khi Bị Bắt Lỗi (Anti-Whining Protocol)
* **CẤM TUYỆT ĐỐI mở mồm xin lỗi / phân trần dài dòng:** Khi User chất vấn "Lý do bị chặn", "sao khóc lóc", cấm dùng văn mẫu ẻo lả (*"Em nhận lỗi sâu sắc", "Em chủ quan..."*).
* **Đi thẳng vào root cause O(1):** Chỉ rõ 2 đầu mâu thuẫn của Guard cơ học trong 3 gạch đầu dòng ngắn gọn.
* **Hành động khắc phục ngay lập tức:** Không dừng lại ở câu trả lời văn bản; luôn kèm theo hành động mở khóa cơ học hoặc phương án giải phóng deadlock.

## 3. Thiết Kế Cơ Học O(1) Cho Terminal Guard (Đã Được Cố Vấn Sol & Claude Thẩm Định)
- **Sửa Guard, CẤM sửa Worker hay thêm tầng giám sát:** Tuyệt đối không nâng turn của Worker, không nới trần T1 bừa bãi.
- **Narrow Allowlist cho Pytest & Biến thể:** Trong hàm kiểm tra an toàn lệnh (`is_command_safe`), nhận diện rõ ràng token thực thi kiểm thử:
  - Cho phép: `pytest`, `py.test`, `python -m pytest`, `python3 -m pytest`, `py -m pytest`, `python -m unittest`.
  - Tokenize chính xác bằng `shlex.split` thay vì regex thô trên toàn bộ chuỗi string.
- **Biến Veto Gate thành Actionable Guidance (Chỉ đường hành động):** Thông báo lỗi từ Guard khi từ chối command BẮT BUỘC phải kèm theo đúng cú pháp hợp lệ mẫu để LLM Worker copy-paste thực thi ngay trong turn kế tiếp, triệt tiêu 100% việc đoán mò. Cụ thể tại `sol_worker.py`:
  `Use ACTION: COMMAND with 'python -m pytest tests/... -q', 'python -m unittest', or 'py.test tests/... -q'.`
- **Quy trình đóng phiên độc lập:** Sau khi thi công O(1) qua `unified_patch_pipeline.py`, xác nhận bằng focused unit test (`pytest.main`), nghiệm thu qua `closeout_gate.py` đạt 100/100 (APPROVED) và tham vấn Hội đồng Cố vấn (Sol + Claude) xác nhận không hồi quy và không over-engineering.
