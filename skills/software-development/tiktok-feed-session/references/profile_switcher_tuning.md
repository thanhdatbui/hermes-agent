# Profile Switcher Tuning & Account Mismatch Recovery

## Hiện tượng lỗi
- Lỗi `profile username still mismatched after switch` xảy ra trên nhiều máy trong ca nuôi (Row 7 hoặc các ca nuôi batch lớn).
- Nguyên nhân: TikTok UI popup switcher tải chậm hoặc không kịp hoàn tất chuyển đổi tài khoản trong 2 lần thử mặc định.

## Cấu hình chuẩn (`python_runner/flows/feed_swipe_smoke.py`)
- `PROFILE_SWITCH_MAX_ATTEMPTS = 3` (dòng ~625, nâng từ 2 lên 3).
- Vòng lặp chuyển profile: `for attempt in range(1, PROFILE_SWITCH_MAX_ATTEMPTS + 1):` (~dòng 16954).
- 3 lần thử giúp các máy yếu / UI lag có thêm cơ hội mở lại switcher dialog và chọn đúng username mong muốn mà không cần thêm code phức tạp hay bypass nguy hiểm.

## Quy trình kiểm tra & Commit an toàn trong `tiktok-luot nuoi acc`
1. **Compile check:**
   ```bash
   "D:/Taadaa/python-envs/automation/Scripts/python.exe" -c "import py_compile; py_compile.compile('python_runner/flows/feed_swipe_smoke.py', doraise=True)"
   ```
2. **Kiểm tra Git Staging:**
   - Luôn chạy `git status` và `git diff --cached` trước khi add/commit.
   - Thận trọng nếu `docs/farm-automation-cases.md` hoặc các file khác đang có sẵn thay đổi staged từ trước; dùng `git restore --staged <file>` để unstage những file không thuộc phạm vi commit.
   - Nếu gặp `fatal: Unable to create '.git/index.lock': File exists`, kiểm tra xem có tiến trình git ngầm chạy hay lock file tồn tại, chờ vài giây hoặc kiểm tra trước khi retry.
3. **Verify diff tối giản:**
   - Dùng `git diff --stat` đảm bảo chỉ sửa đúng dòng mục tiêu trước khi commit.
