# Close Session Code Review Gate & Proxy Migration Lessons (2026-08-20)

## 1. User Correction: "Chốt phiên chưa" / "Chốt chưa" Trigger
Khi user hỏi bất kỳ câu nào liên quan đến chốt phiên:
`"Chốt chưa"`, `"Chốt phiên chưa"`, `"Xong chưa"`, `"Đóng phiên"`, `"Ship được chưa"`.

**QUY TẮC BẮT BUỘC:**
TUYỆT ĐỐI KHÔNG trả lời bằng lời nói suông hoặc bảng tổng kết tự kê nếu chưa thực hiện đủ chuỗi 5 bước khép kín:
1. **Code Review Gate Độc Lập**:
   - Gọi 9Router HTTP API combo `plan-review` (`ag/claude-opus-4-6-thinking` hoặc `gpt-5.6-terra`) với `reasoning_effort: high/max`, `stream: false`, `tools: []`, `tool_choice: "none"`.
   - Bắt buộc kiểm tra `git diff` toàn phiên.
   - Nếu reviewer trả `VERDICT: MINOR_FIXES` hoặc `REJECT`: Sửa ngay các finding cụ thể, sau đó gọi re-review đến khi đạt `VERDICT: APPROVED`.
2. **Pytest Regression Gate**:
   - Chạy toàn bộ test suite liên quan (`test_feed_swipe_smoke_popups.py`, `test_benign_popup.py`,...).
   - Bắt buộc 100% test GREEN.
3. **Merge & Conflict Check**:
   - Kiểm tra `git status -sb` và `git worktree list`, đảm bảo worktree sạch và không có conflict dở dang.
4. **Pull-before-push & Remote Sync**:
   - Chạy `git pull --rebase origin <branch>` rồi `git push origin <branch>`.
5. **Báo Cáo Hoàn Tất Kèm Bằng Chứng**:
   - Báo cáo rõ: (a) Verdict của reviewer độc lập, (b) Số lượng test pass, (c) Commit SHA, (d) Trạng thái `master...origin/master` clean & in-sync.

---

## 2. Bài Học AI Auto-Recovery Git Commit & Pytest Environment
- **Lỗi 1: Xung đột Pillow cp311 (`_imaging`)**:
  - Khi AI Auto-Recovery agent được spawn từ process Hermes, `sys.executable` và `PYTHONPATH` trỏ vào venv của Hermes. Khi chạy pytest test patch mới, Pillow bị crash do mismatch ABI `_imaging` $\rightarrow$ pytest collection error $\rightarrow$ agent tự động rollback patch và báo "commit thất bại".
  - **Khắc phục**: `code_patcher.py` bắt buộc chạy pytest bằng `D:\Taadaa\python-envs\automation\Scripts\python.exe` và loại bỏ `PYTHONPATH` khỏi `os.environ` truyền vào `subprocess.run`.
- **Lỗi 2: Git WinError 2 trong Subprocess**:
  - Background process chạy ngầm thiếu `git` trong `PATH` $\rightarrow$ gọi `git commit` báo `[WinError 2] The system cannot find the file specified`.
  - **Khắc phục**: Khóa cứng đường dẫn tuyệt đối `_GIT_EXE = r"C:\Program Files\Git\cmd\git.EXE"` (fallback `mingw64\bin\git.EXE`).

---

## 3. Khóa Cứng Xoay Dọc 0 Độ Cho Feed Session
- Trên một số thiết bị (Máy 41, Máy 22), hệ điều hành Samsung có thể bị bật `accelerometer_rotation = 1` do WebView hoặc cảm biến gia tốc khi lướt trúng video xoay ngang.
- **Khắc phục**:
  - Gửi lệnh ADB Dual-layer lock (`settings put` + `content insert` vào Content Provider) đưa toàn bộ 78 máy về `accelerometer_rotation = 0` và `user_rotation = 0`.
  - Nhúng trực tiếp `lock_portrait_rotation(ctx)` vào ngay đầu hàm `_feed_session_flow` trong `feed_swipe_smoke.py`.

---

## 4. Parser Cột Video Từ Safe Workbook & Tắt Follow Khi Đổi Proxy
- **Parser `Video Đã Đăng`**:
  - File `taikhoan_run_safe.xlsx` có cột `Video Đã Đăng` (cột 4).
  - Module `core/feed_session_workbook.py` phải định nghĩa `VIDEO_COUNT_COLUMNS = ("video da dang", "video a ang", "so video da dang", "video count", "so video")` (thu hẹp alias, tránh bắt nhầm cột text/URL).
  - Bắt buộc đưa `"video_count": self.video_count` vào `MachineAccount.as_dict()` để không bị thất thoát dữ liệu khi serialize.
- **Tạm Dừng Follow Khi Đổi Dải Proxy & Kill-Switch Strict Boolean**:
  - Khi farm vừa bị lộ dải IP proxy hoặc đổi proxy mới, tạm dừng Follow và Upload trong 1–2 ngày để lướt FYP thuần túy "rửa" trust score cho nick.
  - Sử dụng cờ động có parser boolean nghiêm ngặt: `_env_val in ("1", "true", "yes")` hoặc `ctx.config.get("safety", {}).get("allow_farm_follow")`, TUYỆT ĐỐI KHÔNG dùng `bool("false")` hoặc fallback sang key legacy `safety.allow_cross_repo_follow` để tránh bị bypass ngoài ý muốn.
- **9Router Timeout Cho Code Review**:
  - Khi gọi combo `plan-review` (`gpt-5.6-terra`) hoặc `plan-review-hard` (`gpt-5.6-sol`), diff lớn cần thời gian reasoning nên timeout của HTTP client (`urllib.request`) phải đặt tối thiểu `120s – 180s`. Nếu Terra timeout, 9Router tự động fallback sang `ag/claude-opus-4-6-thinking`.
