# Ground Truth First & Dispatch Cap Discipline (Case 139)

> **Bối cảnh & Sự cố (07/09/2026):**
> Khi gặp lỗi `profile username still mismatched after switch` trên Máy 8, Hermes Coordinator rơi vào vòng xoáy over-engineering kinh điển:
> 1. Đổi 3 giả thuyết liên tiếp mà không một lần quan sát màn hình thật sau khi tap:
>    - Giả thuyết 1: "Do feed drift" -> dispatch worker kiểm tra.
>    - Giả thuyết 2: "Do toạ độ x=540 là khoảng trống chết trên container full-width" -> dispatch worker clamp toạ độ về x=393.
>    - Giả thuyết 3: "Do lệnh tap 0ms bị Android nuốt" -> dispatch worker đổi sang `input swipe 120ms`.
> 2. Chạy lệnh runner PowerShell đồng bộ tại session chính dính timeout 600s làm nghẽn toàn bộ phiên chat.
> 3. Khi Claude Opus High vào audit: Phát hiện cú tap vào toạ độ gốc `x=540` (tâm của container `[0, 600][1080, 816]`) thực tế **hoàn toàn hoạt động và đổi nick ngay lập tức**! Toàn bộ 3 giả thuyết và các bản vá trước đó là "bói toán suy diễn" làm hỏng flow.

---

## 1. Căn Bệnh: Hypothesis Roulette (Cò Quay Giả Thuyết)
- **Cơ chế tâm lý của LLM:** Khi gặp lỗi, model có thiên hướng tự nhiên là thêu dệt câu chuyện kỹ thuật nghe rất hợp lý dựa trên các case lịch sử trong memory/skill, rồi lập tức đẻ hạ tầng (worker, test, patch) để phục vụ câu chuyện đó.
- **Hệ quả:** Ca lỗi kéo dài từ vài phút thành hàng tiếng đồng hồ, sửa sai vị trí, tạo regression trên codebase.

---

## 2. Kỷ Luật Bắt Buộc: Ground Truth First
Trước khi đưa ra bất kỳ nhận định nguyên nhân hay bản vá nào:
1. **BẮT BUỘC chụp ảnh màn hình hiện trường (`screencap`) hoặc dump UI XML:**
   - Quan sát xem màn hình đang ở đâu: Đang ở Profile? Đang ở Bottom Sheet Switcher? Hay bị popup che? Hay bị màn Login/Captcha đá văng?
2. **Quan sát kết quả sau đúng 1 thao tác (Luật 1 biến):**
   - Tap thử toạ độ và chụp ngay 1 ảnh sau 2.5s.
   - Nếu nick đổi -> lỗi nằm ở verify/timing hoặc popup xuất hiện sau khi đổi.
   - Nếu nick không đổi và sheet không đóng -> view chưa nhận click.
   - Nếu văng ra login/re-auth -> session nick đã chết, không phải lỗi code automation.
3. **CẤM sửa code khi chưa có ảnh/XML chứng minh giả thuyết.**

---

## 3. Khóa Cứng Trong Plugin `farm-coordinator-guard`
Đã được mã hoá thành Hard Gate cấp plugin:
1. **Ground Truth First Guard:** Hook `_on_pre_tool_call` chặn đứng `delegate_task` nếu goal/context yêu cầu sửa code/patch mà chưa kèm bằng chứng hiện trường (`.png`, `.xml`, `screencap`, `inspect_machine`).
2. **Dispatch Budget Cap:** Giới hạn cứng `MAX_COORDINATOR_DISPATCHES = 3` worker subagents cho mỗi ca alert. Chặn đứng việc đẻ liên tục 5-7 worker.
3. **Farm Alert FSM Priority:** Ưu tiên phát hiện Farm Alert trước Closeout để template không bị nhận diện nhầm phase.
