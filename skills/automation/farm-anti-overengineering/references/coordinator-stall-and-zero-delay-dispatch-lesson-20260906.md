# Bài Học Sự Cố Treo Phiên 4 Tiếng & Kỷ Luật Zero-Delay Dispatch (06/09/2026)

## 1. Bối cảnh sự cố
Tại phiên trực farm ngày 06/09/2026, nhận Farm Alert Máy 40 (`ce0418244d10342502`) dừng phiên với lỗi `run plan max_duration_seconds exceeded before capture profile_preflight_switch_anchor_2_pre_tap_guard attempt 1`.
Tuy nhiên phiên làm việc bị ngâm kéo dài hơn 4 tiếng không trả kết quả cho người dùng, dẫn đến sự bức xúc tột độ từ phía người dùng (*"Mày ngâm 4 tiếng r hay lắm... Lí do treo 4 tiếng đéo trả kq? Cái đijt mẹ mày lại đéo tuân thủ rule subagent đúng k?"*).

## 2. Các nguyên nhân cốt lõi gây ngâm phiên (Root Causes)

1. **Vi phạm Zero-Delay Dispatch ở Session chính (Coordinator làm sai vai):**
   - Khi chạy `inspect_machine.py 40` gặp lỗi thiếu ADB trong PATH, thay vì bàn giao ngay cho Worker xử lý trong context riêng, Coordinator lại tự ý chạy `find /c` quét ổ đĩa tìm `adb.exe`, rồi dùng tool `patch` trực tiếp sửa file `D:/Taadaa/tools/inspect_machine.py` tại session chính.
   - Hành vi này vi phạm trực tiếp quy tắc: *Coordinator CHỈ inspect hiện trường O(1), CẤM tự sửa code tại session chính.*

2. **Bẫy Timeout 900s do Quét đĩa & Grep diện rộng:**
   - Coordinator chạy các lệnh `grep -rn` và tìm kiếm trên cây thư mục lớn (`.ai-runs`, `python_runner`) trên môi trường Git-Bash Windows. Mỗi lệnh bị treo tối đa 900s (15 phút), làm đóng băng toàn bộ tiến trình chat và ngốn hàng tiếng đồng hồ vô ích.

3. **Subagent đứt gãy và vượt trần thời gian:**
   - Lần dispatch worker 1 bị đứt gãy giữa chừng (`Delegation owner exited before recording a terminal result`).
   - Lần dispatch worker 2 không được siết chặt trần thời gian, worker chạy tới 35 tool calls và ngốn 18 phút (1128s) mới hoàn tất.

4. **Kẹt thời gian trong chính flow máy thật (35 phút kẹt tại hiện trường):**
   - Trong `python_runner/flows/observe.py`, hàm `get_focused_activity` gọi `capture_ui_xml` không có cờ lightweight, khi gặp sự cố ATX session tạm thời đã rơi xuống `_dump_current_ui_unlocked`, kích hoạt toàn bộ ladder phục hồi uiautomator cũ (shell dump retry 1, 2, kill/restart uiautomator, monkey relaunch app x3). Mỗi lần kiểm tra focus ngốn hơn 5 phút. Khi đổi nick bị kẹt liên tiếp, toàn bộ hạn mức 2100s của phiên bị cạn kiệt sạch sẽ.

## 3. Các quy tắc kỷ luật khắc phục triệt để (Non-Negotiable Invariants)

1. **Zero-Delay Dispatch Tuyệt Đối:**
   - Khi nhận Farm Alert có sẵn thông tin (ảnh hiện trường / Serial / Nick): Chạy đúng 1 lệnh inspect O(1) (`python D:/Taadaa/tools/inspect_machine.py <N>`).
   - Kể cả khi inspect gặp lỗi môi trường (như thiếu binary hay path), CẤM TUYỆT ĐỐI Coordinator nán lại fix môi trường hay probe shell. BẮT BUỘC đóng gói toàn bộ hiện trường và gọi `delegate_task` ngay lập tức trong vòng 30 giây!

2. **CẤM Quét Đĩa / Grep Cây Lớn:**
   - Tuyệt đối cấm chạy `grep -rn`, `find`, `search_files` đệ quy trên root repo hoặc thư mục `.ai-runs`, `runs`, `python-envs`.
   - Chỉ được đọc log đích danh: `summary.txt`, `log.jsonl` của run gần nhất hoặc grep có chỉ định file đích cụ thể.

3. **Thứ tự 5 bước Recovery BẮT BUỘC (Không đảo lộn):**
   - B1: Inspect O(1).
   - B2: Phân tích Root Cause từ log cụ thể.
   - B3: Patch Code & Focused Unit Test (DO WORKER THỰC HIỆN TRONG CONTEXT RIÊNG).
   - B4: Canary Test trên máy thật (CHỈ CHẠY SAU KHI CODE ĐÃ ĐƯỢC PATCH & TEST PASS). Tuyệt đối cấm chạy Canary B4 trước khi sửa code!
   - B5: Closeout báo cáo gọn 4 mục (File/hàm đã sửa + kết quả canary).

4. **Kỷ luật Bounded Worker Budget & Canary Gate:**
   - Giao việc cho Worker phải ghi rõ trần: `<=` 15 phút, `<=` 20 tool calls.
   - Khi worker sửa xong, Coordinator verify đĩa bằng `git status --short` và `git diff`.
   - **Thực thi Canary B4 an toàn:** Lệnh canary (`run-feed-session.ps1` hoặc `run-follow.ps1`) là script PowerShell chạy dài. Khi ở Phase ALERT/IDLE (chưa gõ "chốt phiên" để vào Phase CLOSEOUT), Farm Guard Action Guard sẽ chặn cứng các file `.ps1` tại session chính. Do đó, lệnh Canary B4 nên được giao cho Worker Subagent chạy trong background qua `delegate_task`, hoặc Coordinator chỉ chạy Canary trực tiếp sau khi chuyển sang Phase CLOSEOUT (Gate 0 Canary).
