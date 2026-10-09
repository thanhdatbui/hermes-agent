# Worker Analysis Paralysis, WorkerToolGate Cưỡng Chế 2 Tầng & Tự Động Hóa Pre-Flight Canary (06/09/2026)

## 1. Sự Cố Thực Tế: Ngâm Phiên 107 Phút & Đốt 2.1M Token (Máy 9)
Vào ngày 06/09/2026, phiên xử lý Farm Alert Máy 9 (`failed_dismiss_overlay_before_navigation: follow_friends_popup_no_close_control`) bị kéo dài gần 2 tiếng (~107 phút), đốt hơn 2.1 triệu token và 105 tool calls chỉ để thêm 10 dòng guard `if is_main_feed: return False` vào `benign_popup.py`.

### Phân Tích 3 Failure Modes Của 3 Worker:
| Worker | Thời gian & Lượt gọi | Hiện tượng | Nguyên nhân gốc rễ |
| :--- | :--- | :--- | :--- |
| **Worker 1** | 40 phút, 35 turns (max) | Đọc XML, tìm chuỗi regex, so khớp text "Bạn bè" lặp đi lặp lại 35 lần mà **0 lần ghi code**. | **Analysis Paralysis**: Không có tool-call budget cứng, không có phase gate cưỡng chế chuyển từ Inspect sang Write. Context phình lên >2.1M tokens làm latency vọt lên 60-70s / turn. |
| **Worker 2** | 32 phút, 35 turns (max) | Lặp lại đúng vết xe đổ của Worker 1: re-derive root cause từ con số 0. | **Blind Dispatch**: Coordinator không truyền `WORK_PACKAGE` có sẵn vị trí file, hàm, line hint và patch intent. |
| **Worker 3** | 25 phút, 35 turns | Sửa xong code nhưng Canary bị dừng bởi stale lock `machine_9.lock.json` (PID 179800 cũ). | **Unautomated Environment Traps**: Không có pre-flight tự động dọn stale lock và cô lập `$env:PYTHONPATH` (gây xung đột binary `PIL._imaging`). |

---

## 2. Kiến Trúc Khắc Phục 4 Trụ Cột (Thiết Kế Bởi Claude Lead Architect)

### Trụ Cột 1: Contract `WORK_PACKAGE` Giữa Coordinator & Worker
Coordinator làm phần việc nặng về định vị (Intelligence), Worker chỉ thực thi (Execution).
Coordinator **CẤM dispatch mù**. Trước khi gọi `delegate_task`, bắt buộc phải trích xuất:
```json
{
  "target": {
    "file": "python_runner/flows/benign_popup.py",
    "function": "detect_follow_friends_suggestion_popup",
    "line_hint": 4650
  },
  "patch_intent": {
    "strategy": "early_return_guard",
    "pseudocode": "if is_main_feed and not (has_dialog or has_close_control): return False"
  },
  "constraints": {
    "read_budget": 3,
    "write_deadline": 4
  }
}
```

### Trụ Cột 2: PreToolUse Hook Khóa Cứng Worker (`WorkerToolGate`)
Tích hợp trực tiếp vào plugin `farm-coordinator-guard` (`C:/Users/Kibe/AppData/Local/hermes/plugins/farm-coordinator-guard/__init__.py` và git deploy repo):
- **`READ_BUDGET = 3`**: Quá 3 lần gọi tool đọc (`read_file`, `search_files`), hook chặn đứng vật lý (`action: block`):
  `⛔ [WORKER TOOL GATE - READ BUDGET EXHAUSTED]: Ngân sách đọc của Worker đã hết (3/3). Bạn BẮT BUỘC phải gọi write_file hoặc patch ngay bây giờ theo patch_intent! CẤM tiếp tục khảo sát lan man.`
- **`WRITE_DEADLINE = 4`**: Nếu đã qua 4 tool calls mà `write_count == 0`, toàn bộ công cụ đọc bị khóa cứng. Worker bắt buộc phải ghi code (`write_file` hoặc `patch`) ngay lập tức.
- Các công cụ test/compile (`terminal` chạy py_compile / pytest, `git diff`) vẫn được phép để worker nghiệm thu bản vá.

### Trụ Cột 3: Tự Động Hóa Pre-flight Canary (Stale Lock & PYTHONPATH)
Không để worker loay hoay xử lý bẫy môi trường. Tích hợp trực tiếp vào PowerShell runner (`run-feed-session.ps1`):
1. **Cô lập `PYTHONPATH`**: Luôn gán `$env:PYTHONPATH = ""` ở đầu script để triệt tiêu lỗi mismatch binary giữa Hermes venv và venv chạy farm.
2. **Tự dọn Stale Device Lock**:
   - Duyệt qua file `$env:USERPROFILE\.codex\device-locks\machine_${m}.lock.json`.
   - Nếu PID trong file JSON không còn tồn tại (`Get-Process -Id $pid` fail): tự động `Remove-Item -Force` và log `[PRE-FLIGHT] Da xoa stale lock may $m (PID $pid da chet)`.
   - Nếu PID còn chạy và lock quá 600s: xuất cảnh báo tiến trình zombie.

### Trụ Cột 4: Incident Knowledge Cache
- Lỗi `failed_dismiss_overlay_before_navigation: follow_friends_popup_no_close_control`:
  Nguyên nhân: Màn hình Feed chính hiển thị tab "Bạn bè" cạnh tab "Đề xuất". Hàm `detect_follow_friends_suggestion_popup` quét chuỗi con dính chữ "Bạn bè" nên hiểu nhầm Feed là popup gợi ý kết bạn, sau đó fail-closed vì Feed không có nút đóng popup.
  Vá: Bổ sung guard phát hiện Feed chính (có tab "Đề xuất" / "Dành cho bạn" / "For You" hoặc tab "Trang chủ" + video interaction controls) và không có modal dialog thực tế thì `return False` ngay.
