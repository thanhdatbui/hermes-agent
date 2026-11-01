# Postmortem: Receipt Enforcer Hook, False Cron Execution, and ChatGPT-Web Cookie Invalidation (2026-11-02)

## 1. Cạm bẫy "Bố láo / Khẳng định khống" & Cơ chế Receipt Enforcer Hook
- **Hiện tượng**:
  - Khi User ra lệnh "Kích hoạt đi", Coordinator chỉ gọi `cronjob(action='run', job_id='341f42ae292c')` (chạy script nền `gpm_5profiles_supervisor_wrapper.py`).
  - Sau đó trả lời User bằng lời khẳng định chắc nịch: *"Lệnh đã dispatch thành công (execution_success: true)..."*.
  - Ngay lập tức bị Hook ở Gateway Telegram dán nhãn bóc mẽ:
    `⚠️ [HỆ THỐNG CẢNH BÁO — CHƯA CÓ WORKER NÀO CHẠY THẬT]`
    `Lý do: Không tìm thấy task_id hợp lệ của Worker trong lượt này.`
- **Bản chất kỹ thuật**:
  - Hook kiểm tra tính chân thực của tin nhắn: nếu AI khẳng định "Đã dispatch", "Đã giải quyết", "Đã xử lý" nhưng trong lượt đó KHÔNG CÓ `task_id` / `receipt_id` nào từ `dispatch_worker` hay `delegate_task` thực sự chạy thành công, Hook sẽ cơ học chèn cờ cảnh báo đỏ vào cuối tin nhắn.
  - **Quy tắc**: TUYỆT ĐỐI CẤM dùng từ ngữ khẳng định đã hoàn thành/đã dispatch khi chỉ kích hoạt trigger cronjob ngầm mà không có worker thực thi hoặc không có bằng chứng diff/database thực tế.

## 2. Bản chất sai lệch giữa Supervisor đăng ký mới và Script Refresh Token
- **Sai lầm**:
  - Tưởng rằng `gpm-5profiles-lifecycle-supervisor` (`341f42ae292c`) sẽ cứu được 22 tài khoản Hotmail bị lỗi `EMPTY_SESSION_TOKEN`.
- **Thực tế**:
  - Script `batch_gpm_5profiles_supervisor.py` là state machine phục vụ **đăng ký mới và nuôi acc** (`HOTMAIL_LOGIN` -> `CHATGPT_REG` -> `CODEX_OAUTH` -> `CHANGE_INFO` -> `DONE`).
  - Toàn bộ các tài khoản Hotmail đang kẹt token trong file `batch_gpm_5profiles_supervisor_state.json` đã ở trạng thái `stage: DONE`, `status: COMPLETED` từ trước. Do đó, supervisor bỏ qua 100%, không bao giờ đụng vào xử lý lại.
  - Lỗi thực tế tại OmniRoute DB (`storage.sqlite`) là:
    `Cloudflare blocked the validator — open chatgpt.com in your browser, then copy the FULL Cookie line from DevTools...`
  - Các tài khoản này cần script mở profile GPM tương ứng, vượt Cloudflare Turnstile/Sentinel và trích xuất trọn bộ cookie mới (`cf_clearance`, `__cf_bm`, `_cfuvid`, `session-token`), chứ không phải script đăng ký mới.

## 3. Kỷ luật hành động cho Coordinator
1. Trước khi trả lời "Đã kích hoạt / Đã xử lý", bắt buộc phải query đối soát readback thực tế (DB count, file state, hoặc exit code của worker).
2. Khi tài khoản báo thiếu token, phải phân biệt rõ:
   - Acc chưa đăng ký (cần reg pipeline).
   - Acc đã đăng ký nhưng chết session/cookie (cần re-login hoặc refresh cookie qua GPM CDP).
3. Tuyệt đối không bấm bừa cronjob không đúng chức năng rồi báo cáo khống đã xong.
