# Fallback Execution Pattern Khi Claude CLI Hết Quota (05/10/2026)

## 1. Bối cảnh & Hiện tượng
Khi điều phối code surgery hoặc bảo trì gate/guard, người dùng hoặc hệ thống giao việc cho Claude Code CLI (`claude -p`).
Khi Claude Code CLI chạm trần giới hạn (5h session limit hoặc cạn quota subscription):
- Lệnh `claude` trả về: `You've hit your session limit · resets ...` hoặc `CLAUDE_LIMIT_EXCEEDED`.
- **Lỗi điều phối nghiêm trọng**: Coordinator dừng lại, in câu lệnh terminal dài và bảo người dùng tự mở PowerShell ngoài máy để chạy. Người dùng bực mình phản ứng dữ dội vì AI đùn đẩy trách nhiệm và đóng băng tiến độ.

## 2. Nguyên tắc Fallback Bắt buộc (Zero Manual Delegation Friction)
Khi Claude CLI hết quota, Coordinator TUYỆT ĐỐI KHÔNG được:
1. Đùn đẩy lệnh bảo user tự chạy tay ngoài terminal máy host.
2. Đóng băng phiên hoặc báo BLOCKED vô cớ khi các lane AI khác (OmniRoute, Antigravity, Sol, Gemini Worker) vẫn đang online.

## 3. Quy trình Fallback Tự Chủ (Autonomous Lane Spillover)
Thay vì phụ thuộc Claude CLI, Coordinator BẮT BUỘC thực thi chuỗi 3 bước tự động:

### Bước 1: Lập bản vẽ & Patch Contract qua Sol Planner
- Gọi Sol Planner qua tiến trình nền trên host:
  `python D:/Taadaa/tools/sol_planner.py --goal "..." --file "..." --context "..."`
  (Chạy qua OmniRoute port :20129, model `gpt-5.6-sol-high`).
- Thu nhận `sol_plan_id` hợp lệ và anchor duy nhất `c==1`.

### Bước 2: Dispatch Worker Subagent (Antigravity / Gemini Pool)
- Sử dụng `delegate_task` với `TASK_KIND: EDIT` (hoặc `TASK_KIND: INVESTIGATE`).
- Tiêm đầy đủ 6 Gates của Hard Gate #3:
  + `FILE: <duong_dan_tuyet_doi>`
  + `OLD_STRING: <<< ... >>>`
  + `NEW_STRING: <<< ... >>>` (diff <= 30 dòng)
  + `FOCUSED_TEST: python -m py_compile ...`
  + `SOL_PLAN_ID: <sol_plan_id>`
  + `USER_OVERRIDE: Claude CLI quota exhausted, falling back to autonomous worker lane`
  + `FAIL_FAST: Nếu trong <= 3 iterations đầu thấy scope bất khả thi với budget 15 calls thì DỪNG NGAY (ABORT)...`
- Worker thực hiện code surgery chính xác trong sandbox mà không làm bẩn session chính.

### Bước 3: Kích hoạt Runner / Utility qua Allowlist Case C
- Với các tác vụ bảo trì hệ thống hoặc migration phức tạp:
  Worker viết/patch script thực thi tập trung vào `D:/Taadaa/tools/<script>.py`.
  Coordinator kích hoạt chạy qua Allowlist Case C:
  `python D:/Taadaa/tools/<script>.py`
- Xác nhận kết quả bằng `pytest` focused < 30s.

## 4. Kiến trúc 1-Controller Phone Farm: Git Bundle là Single Source of Truth
- **Bẫy Split-Brain**: Giữ file plugin guard sống trong `%LOCALAPPDATA%\hermes\plugins\` rời rạc với Git template trong `D:\Taadaa\Hermes\deploy` làm mất tracking version control khi sửa code.
- **Giải pháp chuẩn hóa**: Gom trọn vẹn plugin (mã nguồn, companion policy engine, unit tests) vào repo Git `D:\Taadaa\Hermes`. Sau đó tạo Directory Junction trên Windows:
  `cmd /c mklink /J "%LOCALAPPDATA%\hermes\plugins\<plugin-name>" "D:\Taadaa\Hermes\deploy\hermes-home\plugins\<plugin-name>"`
- Toàn bộ thay đổi từ runtime sẽ ngay lập tức được Git quản lý, xoá bỏ hoàn toàn bước đồng bộ thủ công.
