# Anti-Disk-Scan Fast Inspection & Error Manifest Routing (2026-09-02)

## 1. Bối cảnh sự cố & Root Cause của Runaway Search Loop
- **Hiện tượng:** Khi nhận tin nhắn Farm Alert (ví dụ: `🚨 [MÁY 10] DỪNG PHIÊN - Lý do: TikTok focus lost to launcher` hoặc `unknown TikTok state`), LLM ở các session mới có phản xạ tự động sinh lệnh `grep -rn "focus lost"` trên toàn bộ repo `python_runner` hoặc chạy script Python `os.walk('D:/Taadaa')`, `glob('**/*', recursive=True)` để tìm file log / nguồn gốc chuỗi lỗi.
- **Hậu quả:** Lệnh bị treo timeout 900s, lặp nhiều vòng lặp liên tiếp làm gián đoạn toàn bộ phiên làm việc của user.

## 2. Quy chuẩn Kỹ thuật: Fast Inspection Tool
Thay vì để LLM tự viết script quét tìm kiếm trên ổ đĩa, toàn bộ thao tác trích xuất hiện trường được chuẩn hóa vào script duy nhất:
`python D:/Taadaa/tools/inspect_machine.py <N>`

### Cơ chế hoạt động (thời gian thực thi < 0.5s):
1. **Lấy Serial & Danh sách nick:** Tra cứu thẳng từ file `taikhoan_run_safe.xlsx` (bảng tĩnh, không quét đĩa).
2. **Kiểm tra Live qua ADB:**
   - Focus hiện tại (`dumpsys window | grep -E "mCurrentFocus|mFocusedApp"`).
   - Trạng thái màn hình khóa / Keyguard (`dumpsys window policy | grep showing`).
   - Timeout màn hình (`screen_off_timeout`, `stay_on_while_plugged_in`).
   - Chụp ảnh màn hình hiện trường lưu ra `MEDIA:D:\Taadaa\m<N>_current.png`.
3. **Đọc Artifact Run Mới Nhất:**
   - Dùng `os.scandir` tầng 1 của `.ai-runs` để lấy đúng folder run mới nhất theo mtime (tuyệt đối không đệ quy).
   - In ra `summary.txt` và 20 dòng cuối `log.jsonl`.
4. **Định tuyến File Cần Sửa (Project Manifest):**
   - Tích hợp `D:\Taadaa\tools\project_manifest.py` để trỏ đích danh file flow phụ trách (`feed_swipe_smoke.py`, `account_switcher.py`, `benign_popup_registry.py`) kèm hướng dẫn fix tương ứng.

## 3. Quy tắc Anti-Pattern cần tránh
- **CẤM chữa cháy bằng ADB:** Tuyệt đối không dùng lệnh `adb shell input` (vuốt, bấm nút) hay sửa `settings` bằng tay để giải quyết tình huống tạm thời trên 1 máy rồi báo xong.
- **BẮT BUỘC sửa Codebase:** Mọi lỗi phát hiện phải được viết thành logic auto-recovery (tự phát hiện + tự xử lý + relaunch/dismiss) vào script chính để toàn bộ 80-160 máy trên farm tự vượt qua trong các ca chạy sau.
