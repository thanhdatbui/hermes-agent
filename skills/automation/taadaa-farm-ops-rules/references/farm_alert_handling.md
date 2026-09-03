# Quy định xử lý Farm Alert & Cấm Quét Đĩa (Grep-R / Search-Files)

## 1. Nguyên nhân gốc rễ dẫn đến vi phạm cấm quét đĩa
Khi nhận Farm Alert (ví dụ `🚨 [MÁY XX] DỪNG PHIÊN ... Lý do: unknown TikTok state`):
- Chuỗi text trong alert thường là nhãn tóm tắt từ watchdog/monitor ngoài, KHÔNG PHẢI tên hàm hoặc chuỗi code có sẵn trong repo.
- Nếu Agent cố chấp chạy `grep -rn`, `search_files`, `find`, `os.walk` để tìm chuỗi alert đó, lệnh sẽ quét đệ quy toàn bộ thư mục -> timeout (15+ phút), treo máy,context bloat và vi phạm nghiêm trọng Farm Safety Rules.

## 2. Quy trình xử lý bất biến (Deterministic Flow)
1. **Trích xuất hiện trường DUY NHẤT:**
   - Chạy: `python D:/Taadaa/tools/inspect_machine.py <N>`
   - Lệnh này trả về: Serial thiết bị, trạng thái live ADB (Focus App, Keyguard), đường dẫn folder run mới nhất, tóm tắt `summary.txt` và log lines cuối.
2. **Đọc log và file flow đích danh:**
   - Đọc `summary.txt` hoặc `log.jsonl` tại đường dẫn run vừa tìm được bằng `read_file`.
   - Mở ĐÚNG file flow phụ trách:
     - Feed / Swipe: `D:/Taadaa/tiktok-luot nuoi acc/python_runner/flows/feed_swipe_smoke.py`
     - Popup / Dismiss: `D:/Taadaa/tiktok-luot nuoi acc/python_runner/flows/benign_popup.py`
     - Device setup: `D:/Taadaa/tiktok-luot nuoi acc/python_runner/flows/device_prepare.py`
3. **Tuyệt đối cấm:**
   - CẤM `grep -r`, `grep -rn`, `search_files` quét diện rộng thư mục `python_runner` hoặc toàn repo.
   - CẤM đoán mò hoặc cố tìm chuỗi text alert trong codebase.
