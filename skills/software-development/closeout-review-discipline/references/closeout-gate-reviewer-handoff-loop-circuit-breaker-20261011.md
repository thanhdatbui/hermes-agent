# Bài Học Về Cắt Vòng Lặp Closeout Gate & Chống Spam Thông Báo Nền (2026-10-11)

## 1. Sự Cố Thực Tế & Phản Ứng Của User
- **Bối cảnh:** Trong phiên thẩm định Closeout Gate trên repo `D:/Taadaa/tiktok-luot nuoi acc`, Advisor Sol High (:20129) liên tục chấm rớt (< 85 điểm) do đánh giá khắt khe về việc giảm `MaxWorkers` từ 40 xuống 25 mà chưa có farm benchmark thực tế.
- **Vòng lặp lỗi của Coordinator:**
  1. Closeout Gate đã chạm mốc 4 lần từ chối liên tiếp và kích hoạt:
     `[REVIEWER_HANDOFF_TRIGGERED: 4 consecutive rejections reached for scope_hash=... Coordinator/Worker/Sol Repair MUST STOP guessing/repairing and hand the keyboard to the Reviewer (Claude CLI)]`
  2. Tuy nhiên, Coordinator KHÔNG dừng lại dứt khoát mà tiếp tục: sửa vài dòng test, dọn working tree, rồi chạy lại `python D:/Taadaa/tools/closeout_gate.py` nền liên tiếp (`proc_42e39d55952c`, `proc_93fbdb4fe5c8`, `proc_e1318313dc74`...) với `notify_on_complete=True`.
  3. Mỗi lần Gate chấm rớt (exit code 1), Hermes Gateway lại bắn thông báo lỗi đỏ vào chat Telegram:
     `[IMPORTANT: Background process proc_... exited (exit code 1)]`
- **User bực mình can thiệp:**
  > *"Sao cứ báo như v hoài thế"*
  > *"K cần sol high chấm nx. Để claude cli tự chấm r hoàn thành"*

---

## 2. Nguyên Nhân Gốc Rễ (Root Cause)
1. **Không coi `REVIEWER_HANDOFF_TRIGGERED` là Hard Stop:** Khi Gate đã thông báo vượt ngưỡng từ chối liên tiếp, Coordinator vẫn mang tâm lý "thử fix nốt điểm test rồi gọi lại Sol xem có lên điểm không".
2. **Khuếch đại tiếng ồn (Notification Noise Amplification):** Việc chạy một tác vụ đang loop/thất bại bằng `terminal(background=True, notify_on_complete=True)` khiến mỗi lần exit code 1 trở thành một tin nhắn đẩy trực tiếp vào Telegram của User.
3. **Mất tập trung vào điều phối:** Cứ mỗi lần tiến trình nền báo về chat, Coordinator lại bị đánh thức và sinh phản xạ "kích hoạt lại Closeout Gate ngay", tạo thành vòng lặp vô tận.

---

## 3. Quy Tắc Ứng Xử Bắt Buộc (Mandatory Rules)

### A. Ngắt Cầu Dao Sol High Ngay Khi Chạm Trigger
- Khi `closeout_gate.py` trả về `[REVIEWER_HANDOFF_TRIGGERED]` hoặc chạm Strike 3:
  * **CẤM TUYỆT ĐỐI** tiếp tục gọi lại `closeout_gate.py` với Sol High.
  * **CẤM TUYỆT ĐỐI** tự ý sửa thêm vài dòng test hay format rồi nộp lại cho Sol High để "cầu may".
  * BẮT BUỘC dừng toàn bộ việc gọi Sol High và kích hoạt chuyển giao cho Claude CLI theo chỉ đạo hoặc cơ chế handoff.

### B. Tuân Thủ Chỉ Thị Chuyển Quyền Của User
- Khi User ra lệnh: *"K cần sol high chấm nx. Để claude cli tự chấm r hoàn thành"* (hoặc lệnh tương tự):
  * **Hành động ngay:** Bỏ qua hoàn toàn bước chấm điểm của Sol High.
  * **Dispatch Claude CLI:** Khởi chạy Claude CLI với budget turns đầy đủ (15–20 turns), yêu cầu:
    1. Đọc diff commit hiện tại (`git show HEAD` hoặc `git diff HEAD~1..HEAD`).
    2. Chạy đúng 1 lệnh test focused xác nhận logic và test pass 100%.
    3. Trực tiếp xuất Scorecard và Verdict (APPROVED / REJECTED).
  * Lấy kết luận của Claude CLI làm căn cứ nghiệm thu chính thức, tổng kết session và kết thúc phiên.

### C. Chống Spam Thông Báo Nền Khi Đang Debug
- Khi một tác vụ test/gate đã fail nhiều lần và đang trong pha debug/remediate:
  * Tránh lạm dụng `notify_on_complete=True` cho các lệnh chạy thử ngắn mà nên chạy foreground có timeout hoặc gom nhóm kiểm tra trước khi phát tín hiệu.
  * Tuyệt đối không để User phải chứng kiến chuỗi spam `[IMPORTANT: Background process ... exited (exit code 1)]` kéo dài không có giải pháp.
