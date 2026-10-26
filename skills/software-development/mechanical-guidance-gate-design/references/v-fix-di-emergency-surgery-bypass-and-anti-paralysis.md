# Pitfall & Quy Trình: Lệnh "Fix đi" / "V fix đi", Gate DENY & Chống Bại Liệt Xin Phép Lại

## 1. Hiện Tượng Thực Tế (Sự Cố Session 26/10/2026)
- User nhận báo cáo 6h và hỏi về nguyên nhân Kibe đứng yên.
- Sau khi được giải thích, User ra lệnh rõ ràng: `V fix đi`.
- Coordinator dispatch `delegate_task` cho Worker nhưng gặp liên hoàn lỗi Coordinator Guard:
  1. `MISSING_TASK_KIND`
  2. `EDIT_MISSING_FILE`
  3. `EDIT_MISSING_OLD_STRING`
  4. `DIFF_BUDGET_EXCEEDED` (> 30 dòng).
- Khi chạm trần iteration, Coordinator dừng lại và xuất tin nhắn tóm tắt phương án, kèm câu chốt chờ xác nhận: *"Khi anh cần triển khai bản vá này vào codebase, em sẽ thực hiện ngay..."*.
- User nổi nóng phản ứng: *"T đã chat v fix đi r mà? Cái đéo gì v cứ chờ xác nhận v sáng nay session nào cũng hỏi lại v"*.

## 2. Nguyên Nhân Gốc Rễ
1. **Thiếu phản xạ kích hoạt Emergency Surgery (L2):** Thang leo thang đã quy định rõ: Sau 2 lần thất bại cấu trúc (Structural failures / Gate DENY do contract/budget) khi dispatch Worker VÀ đã có exact diff -> Coordinator ĐƯỢC CẤP SẴN QUYỀN tự sửa trực tiếp qua L2.
2. **Sai lầm xin phép lại khi đã có lệnh trực tiếp:** User đã ra lệnh hành động (`V fix đi`). Việc dừng lại giải trình phương án và hỏi lại bị coi là trốn tránh trách nhiệm và gây ức chế tột độ cho User (vi phạm User Profile: "Vibe O(1), bực=làm ngay; Gate DENY=Auto-Rewire tự chữa ngầm, cấm BLOCKED đùn việc hay phân trần lòng vòng khi user giục").

## 3. Quy Trình Cơ Giới Hóa Bắt Buộc (Anti-Paralysis Execution)
Khi User đã ra lệnh `Fix đi` / `V fix đi` / `Làm đi`:
1. **Nếu dispatch Worker bị Gate DENY (contract violation hoặc DIFF_BUDGET_EXCEEDED):**
   - Không được spam dispatch lại với cùng lỗi hay buông xuôi hỏi lại user.
   - Kiểm tra ngay: Đã có exact diff chưa? Nếu có exact diff và scope có thể cô đọng về $\le 30$ dòng:
     -> **KÍCH HOẠT NGAY EMERGENCY SURGERY (L2)** trong session chính.
2. **Kỷ luật thực thi L2 Surgery:**
   - Dùng `patch` trực tiếp trên file target.
   - Giữ diff tinh gọn $\le 30$ dòng (kiểm tra bằng `git diff --numstat` trước commit).
   - Chạy 1 test focused duy nhất qua `terminal` hoặc `pytest` $< 30$s.
   - Commit với tiền tố `[L2-surgery]`.
   - Chạy script sync (ví dụ `cron_sync_watchdog.py`) đồng bộ sang OneDrive/Runtime.
3. **Phản hồi nghiệm thu:**
   - Báo cáo kết quả bằng chứng thực tế (test passed, diff numstat, commit hash, mẫu output mới).
   - Tuyệt đối không hỏi lại *"Anh có muốn áp dụng không"*.
