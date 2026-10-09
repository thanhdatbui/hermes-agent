# Prompt Misattributed File Trap, Unbounded Git Log Timeout & Safe Verification (06/09/2026)

## 1. Bối cảnh
Người dùng hoặc alert prompt yêu cầu:
`Sửa lỗi UnboundLocalError recaptured_xml trong python_runner/flows/observe.py repo tiktok-luot nuoi acc`

Khi kiểm tra `observe.py` (cả hàm `observe_current_screen` và toàn bộ file):
- Biến `recaptured_xml` **hoàn toàn không tồn tại** trong file.
- Hàm `observe_current_screen` sử dụng `xml_text`, `current_xml_text`, `xml_result` và truyền `raw_xml=current_xml_text` vào `safety_check(...)`.

Thực tế qua kiểm tra lịch sử commit và session trước:
- Lỗi `UnboundLocalError: cannot access local variable 'recaptured_xml'` thực chất xảy ra trong `python_runner/flows/feed_swipe_smoke.py` ở hàm `verify_and_switch_profile` (khối placeholder check bị đặt sai thụt lề ra ngoài khối `except AccountSwitcherError:`).
- Lỗi này đã được vá dứt điểm tại commit `af9968d` (Case 126) và bổ sung an toàn tại commit `bcee621` (Case 127).

---

## 2. Các cạm bẫy chết người (Pitfalls)

### Cạm bẫy 1: Prompt Misattribution dẫn tới phản xạ "quét đĩa diện rộng"
- **Hiện tượng:** Khi không tìm thấy từ khóa `recaptured_xml` trong file `observe.py`, agent hoang mang cho rằng từ khóa nằm ở file khác hoặc repo khác, liền chạy `os.walk('D:/Taadaa')` hoặc quét đệ quy tìm kiếm.
- **Hậu quả:** Ổ `D:/Taadaa` chứa hàng triệu file (`.git`, `runs`, `runtime`, `python-envs`), lệnh Python `os.walk` bị nghẽn I/O và dính timeout 900s (15 phút) liên tiếp, làm cạn kiệt ngân sách lượt gọi.
- **Giải pháp chuẩn:**
  1. Dùng kiểm tra O(1) trên đúng file prompt yêu cầu:
     ```python
     python -c "with open('D:/Taadaa/.../observe.py', encoding='utf-8') as f: print([line for line in f if 'recaptured_xml' in line])"
     ```
  2. Nếu xác định biến KHÔNG có trong file: **DỪNG LẠI NGAY**, cấm quét đĩa!
  3. Kiểm tra nhanh 5 commit gần nhất: `git log -n 5 --oneline` để xem context gần đây của repo.
  4. Hoặc tra cứu nhanh session DB bằng `session_search(query="recaptured_xml")` chỉ mất 1 giây.
  5. Báo cáo trung thực: File được chỉ định không chứa biến lỗi, giải thích rõ lỗi từng phát sinh ở đâu và đã được commit nào xử lý.

### Cạm bẫy 2: `git log -S <symbol> -p` không giới hạn file gây Timeout 900s
- **Hiện tượng:** Chạy `git log -S recaptured_xml -p -n 3` trên toàn repo `tiktok-luot nuoi acc`.
- **Hậu quả:** File `feed_swipe_smoke.py` dài hơn 22.000 dòng. Lệnh `git log -S -p` ép git phải sinh unified diff trên toàn bộ các commit lớn, làm bash treo cứng và dính timeout 900s.
- **Giải pháp chuẩn:**
  - Tuyệt đối không dùng `-p` khi search commit diện rộng trên monolith repo.
  - Dùng `--oneline` hoặc `--name-only`:
    ```bash
    git log -S "recaptured_xml" --oneline -n 5
    ```
  - Nếu muốn xem diff, bắt buộc chỉ định rõ file:
    ```bash
    git log -S "recaptured_xml" -p -n 1 -- python_runner/flows/feed_swipe_smoke.py
    ```

### Cạm bẫy 3: Đường dẫn MSYS `/d/...` trên công cụ `search_files`
- **Hiện tượng:** Gọi `search_files(path="D:/Taadaa/tiktok-luot nuoi acc/...")` nhưng truyền dạng `/d/Taadaa/...` vào tool `search_files`.
- **Hậu quả:** Công cụ `search_files` chạy ripgrep native trên Windows, không hiểu mount path `/d/` của MSYS bash, báo lỗi:
  `Search failed: rg: /d/...: The system cannot find the path specified. (os error 3)`.
- **Giải pháp chuẩn:** Luôn dùng đường dẫn chuẩn Windows `D:/...` hoặc `D:\...` khi gọi `search_files` và `read_file`.
