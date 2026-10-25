# Compliance Watchdog Auto-Rewiring & Guidance Injection SOP

## 1. Context & User Directive
Khi nhận báo cáo định kỳ từ `farm-gate-compliance-6h-report` (hoặc 24h compliance watchdog) cảnh báo các Gate bị FAIL:
- **CẤM TUYỆT ĐỐI:** Phân tích suông, đọc lại số liệu vi phạm rồi dừng lại hoặc giải thích lòng vòng.
- **BẮT BUỘC:** Chuyển ngay sang kế hoạch hành động 2 mũi giáp công: (1) Auto-Wiring / Active Pivot tại các chốt chặn, (2) Nạp Guidance kiến trúc O(1).

## 2. Bóc tách 4 điểm nghẽn phổ biến nhất từ Audit Logs

### A. Gate G3 - Worker Dispatch Gate
1. **`[Worker Dispatch] investigate` (Missing Budget):**
   - **Hiện tượng:** `delegate_task` bị chặn bởi Hard Gate #3 do không tìm thấy `BUDGET: <= N calls`.
   - **Auto-Wiring:** Tầng Pre-Dispatch Gate phải tự động mutate prompt: prepend `BUDGET: <= 8 calls. FAIL_FAST: Dừng ngay trong <= 3 bước nếu không khả thi.` nếu prompt là route điều tra nhưng thiếu budget, thay vì quăng DENY câm.
2. **`[Worker Dispatch] subagent_edit_blocked`:**
   - **Hiện tượng:** Agent dùng `delegate_task` để sửa code thay vì `dispatch_worker.py`.
   - **Auto-Wiring:** Tự động chuyển hướng (Auto-Rewire) sang `pythonw D:/Taadaa/tools/dispatch_worker.py --workdir <dir> --file <target> "<prompt>"`.

### B. Gate G7 - Anti-Scan & Terminal Guard
1. **`GUARD_SEARCH_FILES_ROOT` & `GUARD_DANGEROUS_ROOT`:**
   - **Hiện tượng:** `search_files` gọi trên `D:/Taadaa/tools` hoặc script chứa `os.walk`/`glob(recursive=True)` quét thư mục hệ thống gây nghẽn I/O.
   - **Guidance:** Tuyệt đối không dùng `search_files` hoặc `os.walk` từ root. Luôn nhắm trực tiếp vào file cụ thể hoặc dùng `os.listdir()` ở 1 cấp thư mục.

### C. Gate G8 - Cronjob Window Guard
1. **`CONSOLE_WINDOW`:**
   - **Hiện tượng:** Script chạy nền hoặc cronjob gọi `python` trực tiếp làm bật cửa sổ CMD cướp focus màn hình của User.
   - **Auto-Wiring & Fix:** Bắt buộc dùng `pythonw` hoặc truyền cờ `creationflags=subprocess.CREATE_NO_WINDOW` (0x08000000) vào mọi lệnh `subprocess.run` / `subprocess.Popen` trên Windows.

## 3. Quy trình nạp Guidance O(1)
- **Cho GuardGate Invariants:**
  ```bash
  python D:/Taadaa/tools/guardgate/update_guidance.py --rule-id "<rule_id>" --guidance "<bài học kiến trúc>"
  ```
- **Cho Dynamic Skills Thư viện Farm:**
  ```bash
  python D:/Taadaa/tools/record_skill_knowledge.py --skill "<skill_name>" --content "<quy trình chuẩn>"
  ```
