# Subagent Lobotomy via Hard Block Guards & The Natural Steering Paradigm
*(Claude Opus High Architectural Audit & Case Study — 07/09/2026)*

## 1. Sự Cố Hiện Trường: 45 Phút Ngâm Phiên & Subagent Bị "Ngọng"
- **Hiện tượng:** Coordinator dispatch worker chạy script bật 2FA trên Máy 1. Script chạy 1 phút văng `SWITCHER_OPEN_FAILED`. Thay vì báo cáo và thoát, worker subagent tự ý đi đọc ngược `automation-core`, gọi `computer_use`, chạy `search_files` và loop 33 tool calls suốt 45 phút không báo cáo về session chính.
- **Phản ứng sai lầm ban đầu (Band-aid):**
  - Coordinator hạ `max_iterations: 12` và siết chặt thêm các tầng guard: cấm `computer_use`, đếm `READ_BUDGET=3`, `WRITE_DEADLINE=4`, chặn terminal bằng allowlist nhỏ giọt.
  - User phản ứng gay gắt: *"Tào lao. Revert lại, tự nhiên k cho dùng computer use. Mấy cái của m khiến cho sub agent ngọng luôn ấy. Hỏi claude cli xem"*.
- **Tư vấn từ Claude Opus High:** User đúng 100%. Giảm tool hay đếm tool là cắt ngọn, và việc thêm các tầng Hard Block Guard ở hook execution chỉ làm subagent bị "cắt não" (lobotomized / choked).

## 2. Bản Chất Kỹ Thuật: Tại Sao "Hard Block Guard" Luôn Thất Bại?
1. **Ý định không bị xóa, chỉ có năng lực bị xóa:**
   - LLM là hàm autoregressive. Khi nhận task, nó có ý định hoàn thành.
   - Khi bị chặn bằng `action: block` ở hook, ý định vẫn nguyên vẹn. Model chỉ hiểu là tool đó không chạy được $\rightarrow$ nó thử biến thể khác (thử tool khác, thử đường vòng vụng về). Chặn tool không đổi được hành vi, chỉ biến agent thành kẻ bối rối.
2. **Context Poisoning $\rightarrow$ Doom Loop:**
   - Mỗi lần bị hook chặn, một chuỗi lỗi `⛔ [BLOCKED]` được nhồi vào context.
   - Sau vài lượt, context trông giống hệt một phiên làm việc đang đổ vỡ toàn diện. Model autoregressively bám theo phân phối của context và biểu hiện đúng tính cách của một agent bối rối, thất bại, "ngọng".
3. **Adversarial Counter là tệ nhất:**
   - Các bộ đếm (`READ_BUDGET`, `MAX_WORKER_CALLS`) tạo ra trò chơi đối kháng bịt mắt model. Model không quan sát được state rõ ràng $\rightarrow$ hoảng loạn hoặc dè dặt không thu đủ dữ liệu $\rightarrow$ chẩn đoán sai và ngâm phiên lâu hơn.
4. **Sai tầng kiểm soát:**
   - Tool = Năng lực (Capability).
   - Behavior = Mục tiêu + Tiêu chí dừng (Intent + Stopping Criteria).
   - Đang cố kiểm soát hành vi bằng cách bóp nghẹt năng lực ở tầng hook out-of-band là anti-pattern kinh điển.

## 3. Cách Các Hệ Thống Multi-Agent Đỉnh Cao Kiểm Soát Subagents
Không một hệ thống hàng đầu nào (Claude Code, Deep Research, SWE-bench top) dùng hook để đếm số lệnh hay chặn tool nhỏ giọt. Chúng định hình hành vi qua 4 đòn bẩy ở tầng context/prompt:
1. **Context Boundary:** Subagent nhận context sạch, hẹp của đúng 1 thiết bị / 1 nhóm việc, không gánh việc toàn cục.
2. **Clear Stopping Criteria:** Tiêu chí dừng khách quan, quan sát được (*"Xong khi nhìn thấy màn hình X hoặc log trả về Y"*).
3. **Structured Output / Return Contract:** Ép subagent trả về đúng một schema kết quả (`{status, reason, evidence}`). Ép nó hội tụ về deliverable thay vì đi lang thang.
4. **Natural Incentives:** Cung cấp đầy đủ công cụ $\rightarrow$ Model làm được việc nhanh $\rightarrow$ **Nó tự kết thúc sớm**. Bóp nghẹt tool $\rightarrow$ Model không về đích được $\rightarrow$ **Nó không thể dừng và càng ngâm phiên**.

## 4. Quy Chuẩn Runner Terminal Contract (Định Nghĩa Lại Definition of Done - DoD)
- **DoD Cũ (Success-Biased):** "Chạy, lấy secret thật, nhập OTP và ghi vào Excel, chụp ảnh xác nhận".
  $\rightarrow$ Lỗi `SWITCHER_OPEN_FAILED` bị hiểu là *chưa xong*, model tự động chuyển vai thành debugger.
- **DoD Mới (Report-Biased):** "Ghi nhận kết cục thực tế và THOÁT NGAY".
  $\rightarrow$ `TERMINAL = DONE`: Bất kể kết quả là `success` hay `failed` (`SWITCHER_OPEN_FAILED`, `CAPTCHA`, `OTP_ADVANCE_BUTTON_NOT_REACHED`), đều là **HOÀN THÀNH 100% NHIỆM VỤ**.
  $\rightarrow$ Lỗi của thiết bị là **DỮ LIỆU cần báo cáo về cho Coordinator**, KHÔNG PHẢI bài toán mà Runner được phép tự ý nhảy vào giải.

## 5. Khung Prompt Chuẩn (Soft Steering)
Khi Coordinator dispatch subagent, bắt buộc tuân theo cấu trúc:
```text
NHIỆM VỤ: <Trách nhiệm cụ thể, đơn nhất trên Máy N>
CÔNG CỤ: Full access (terminal, computer_use, read/write). Dùng bất kỳ công cụ nào cần thiết.
XONG KHI: <Tiêu chí dừng khách quan: có exit code / output / screencap>
NẾU BẾ TẮC: Thử tối đa 1-2 lần không tiến triển thì DỪNG và trả về {status: "blocked", reason: ...}. CẤM lặp vô hạn.
TRẢ VỀ: JSON {status, reason, evidence}. Báo cáo ngắn gọn và THOÁT NGAY.
```

## 6. Những Gì Được Giữ & Bỏ Ở Tầng Hook
- **XÓA BỎ HOÀN TOÀN:**
  - `READ_BUDGET`, `WRITE_DEADLINE`, `MAX_WORKER_CALLS`.
  - Whitelist terminal nhỏ giọt (`is_safe_terminal_verify`).
  - Mọi silent block chặn công cụ (`computer_use`, `read_file`, `patch`).
- **CHỈ GIỮ LẠI 3 INVARIANT AN TOÀN THẬT SỰ:**
  1. Destructive actions: Chặn lệnh phá hoại hạ tầng thật (`rm -rf /`, format ổ đĩa, adb wipe toàn dàn máy).
  2. Rò rỉ credential / private key ra ngoài.
  3. Blast radius: Giới hạn chỉ tác động lên đúng thiết bị được giao.
