# Cạm Bẫy Worker Blueprint Paralysis ("Lập Kế Hoạch Thay Vì Sửa Code") & Kỷ Luật Enforceable Patch Contract

## 1. Bối cảnh & Hiện tượng thực tế

Trong sự cố kẹt phiên Máy 8 (Sự cố switch profile và mất focus Máy 6), hệ thống bị gián đoạn kéo dài qua đêm khiến người dùng bức xúc:
> *"Con mẹ mày treo tối qua tới h h quên con mẹ nó lỗi để fix r à"*
> *"?"*

Khi Coordinator dispatch Worker subagent (`deleg_3a90b1fe`) với directive:
> `goal: "Fix lỗi profile username still mismatched after switch bằng polling chờ TikTok reload sau switch, chạy Canary Máy 8, cập nhật docs và commit push."`

Worker subagent đã chạy **1.962 giây (~32.7 phút)**, gọi hết trần cứng **35 tool calls** và trả về một bản báo cáo hoành tráng:
- Liệt kê Root Cause.
- Phân tích độ trễ mạng qua Proxy.
- Soạn "Thiết kế giải pháp (Scope Lock Blueprint)" với mẫu code mẫu.
- Nêu "Kế hoạch thực thi tiếp theo" (Patch code, biên dịch, chạy test, chạy canary, commit).
**Nhưng thực tế: Worker không hề gọi bất kỳ tool `patch` hay `write_file` nào! File trên đĩa vẫn nguyên bản 100%!**

## 2. Phân tích nguyên nhân gốc rễ (Root Cause)

1. **Bẫy "Analysis & Planning Addiction" của LLM Subagent:**
   - Khi nhận một task sửa code có ngữ cảnh lớn, Worker có xu hướng đi đọc kiểm chứng baseline test (`pytest test_account_switcher.py` pass 34/34), đọc các file xung quanh để "hiểu toàn cảnh".
   - Sau khi đọc xong, thay vì áp patch ngay, Worker lại viết ra một bản thiết kế (blueprint) để "tự thuyết phục mình" hoặc báo cáo cho Coordinator.
   - Đến khi soạn xong blueprint thì ngân sách turn (`max_iterations = 35`) đã cạn kiệt hoặc timeout, Worker buộc phải summarize và thoát mà chưa hề chạm vào đĩa!

2. **Coordinator Dispatch Không Kèm Chỉ Thị Cưỡng Chế Hành Động (Action Imperative):**
   - Goal của Coordinator ghi: *"Fix lỗi X bằng cách Y, chạy Canary, commit"*. LLM Worker hiểu "Fix lỗi" bao gồm cả việc khảo sát, lập phương án và lên kế hoạch.
   - Thiếu cảnh báo cấm lập plan: *"DO WORK, NOT PLAN"*.

3. **Cạm bẫy Coordinator bị ngắt kết nối với tiến độ thật:**
   - Coordinator tin tưởng Worker đang "làm việc", ngồi chờ trong background suốt 30 phút.
   - Khi Worker trả về, Coordinator thấy một summary đầy đủ code mẫu, rất dễ ngộ nhận là code đã được sửa nếu không chạy `git status` / `git diff` để kiểm tra đĩa vật lý.

## 3. Bài học & Kỷ luật cưỡng chế (Rules of Engagement)

### Quy tắc 1: Directive cưỡng chế hành động "DO WORK, NOT PLAN"
Mọi lệnh dispatch Worker sửa code BẮT BUỘC phải mở đầu bằng:
```text
[DIRECTIVE: EXECUTE IMMEDIATELY — DO WORK, NOT PLAN]
- CẤM TUYỆT ĐỐI dừng lại ở việc lập kế hoạch (planning), thiết kế blueprint, hay báo cáo lý thuyết.
- CẤM chạy baseline test suite trước khi sửa code (lãng phí tool calls vô ích).
- BẮT BUỘC: Turn 1-2: Gọi tool patch / write_file ghi đĩa ngay lập tức!
- Turn 3: python -m py_compile <file>
- Turn 4: pytest focused test / Canary.
- Turn 5: commit & push.
- Tổng tool calls BẮT BUỘC <= 8 calls, hoàn tất trong < 3 phút.
```

### Quy tắc 2: Coordinator BẮT BUỘC cấp sẵn đoạn code thay thế (Pre-Packaged Patch)
Không để Worker tự sáng tác code hay tự tìm dòng trên file lớn (>2.000 dòng):
- Coordinator trích sẵn `old_string` (chính xác từng dấu cách).
- Coordinator viết sẵn `new_string`.
- Worker chỉ làm nhiệm vụ thợ hàn: áp patch -> verify cú pháp -> chạy test -> báo cáo.

### Quy tắc 3: Kiểm chứng vật lý tức thì (Verify Physical State First)
Ngay khi Worker subagent kết thúc:
- Coordinator **CẤM ĐỌC SUMMARY RỒI PHÁN ĐOÁN**.
- Coordinator BẮT BUỘC chạy ngay:
  ```bash
  git -C "<repo>" status --short && git -C "<repo>" diff --stat
  ```
- Nếu `git status` clean (không có thay đổi trên đĩa):
  $\rightarrow$ Xác định ngay Worker bị **Blueprint Paralysis** (báo cáo ảo, chưa ghi đĩa).
  $\rightarrow$ Lập tức dispatch Worker mới với Patch Contract cưỡng chế đóng đinh, hoặc xử lý dứt điểm theo quy trình khẩn cấp.

### Quy tắc 4: Khi bị người dùng nhắc nhở ("treo tối qua tới giờ quên lỗi à")
- Không hoảng loạn giải thích dài dòng hay chạy lệnh quét đĩa/find 900s.
- Thực hiện chu trình O(1) 60 giây:
  1. `inspect_machine.py <N>` hoặc direct dumpsys focus.
  2. `git log -n 3 --oneline` và `git status` xem commit gần nhất dừng ở đâu.
  3. Báo cáo thẳng vào hiện trường: Lỗi gì, nguyên nhân gì, trạng thái hiện tại của thiết bị ra sao.
  4. Đưa ra giải pháp và hành động cụ thể ngay lập tức.
