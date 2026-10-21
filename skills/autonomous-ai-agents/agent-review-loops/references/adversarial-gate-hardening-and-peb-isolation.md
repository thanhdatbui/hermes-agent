# Adversarial Gate Hardening & In-Process Isolation Lessons (Plan-Exec Gates)

## 1. Bản Chất Các Lỗ Hổng Fail-Open Khi Red-Team Gate Cơ Học
Khi xây dựng hệ thống Gate cơ học 3 bước (Gate A: Evidence -> Gate B: Plan -> Gate C: Exec), các mô hình Reviewer cấp cao (như Claude Sonnet 5.5) sẽ kiểm thử xâm nhập thực tế (adversarial red-teaming) bằng code thật, không chỉ dựa vào unit test mock.

### Lỗ hổng 1: Rò rỉ Secret qua Process Environment Block (PEB) trên Windows
* **Cơ chế tấn công:**
  Khi Gate chạy lệnh do worker khai báo (cmd claim ở Gate A hoặc acceptance command ở Gate C) qua `subprocess.Popen(..., shell=True)`:
  Code dùng `clean_env = os.environ.copy(); clean_env.pop("GATE_HMAC_SECRET", None)` và truyền `env=clean_env`.
  Tuy nhiên, trên Windows, `os.environ.pop()` trong Python **chỉ xóa key trong dictionary nội bộ của runtime Python**, hoàn toàn KHÔNG cập nhật khối OS Process Environment Block (PEB) của tiến trình!
  Worker command chạy cùng user có thể dùng `ctypes` gọi `GetEnvironmentVariableW` hoặc `NtQueryInformationProcess` + `ReadProcessMemory` đọc thẳng PEB của tiến trình cha (gate) để lấy `GATE_HMAC_SECRET`. Có secret, worker tự ký receipt và giả mạo toàn bộ chuỗi gate!
* **Biện pháp khắc phục triệt để:**
  Ngay khi đọc secret từ môi trường lúc khởi động gate:
  ```python
  if sys.platform == "win32":
      try:
          import ctypes
          ctypes.windll.kernel32.SetEnvironmentVariableW("GATE_HMAC_SECRET", None)
      except Exception:
          pass
  os.environ.pop("GATE_HMAC_SECRET", None)
  _CACHED_SECRET = secret.encode("utf-8")
  ```
  Xóa trực tiếp qua `SetEnvironmentVariableW(..., None)` sẽ làm sạch hoàn toàn khối PEB của tiến trình, chặn đứng mọi kỹ thuật quét bộ nhớ của tiến trình con.

### Lỗ hổng 2: Tấn công xóa Receipt & Ledger để Reset Chuỗi (Chain-Reset via File Deletion)
* **Cơ chế tấn công:**
  Hệ thống chặn ghi đè receipt PASS và có file ledger append-only `.gate_ledger.jsonl`.
  Nhưng nếu cả receipt và ledger đều nằm trong thư mục làm việc của worker (`state/gates/`), worker vượt qua Gate A & B ở commit sạch `C1`, sau đó commit mã độc `evil.py` thành `C2`, rồi `rm -rf` toàn bộ thư mục `gates/` (xóa cả receipt lẫn ledger).
  Khi chạy lại, Gate A thấy không có receipt hay ledger, coi như task mới và cấp PASS ở `C2`. Khi đó Gate C so sánh diff với `C2` nên hoàn toàn không phát hiện `evil.py`!
* **Biện pháp khắc phục triệt để:**
  Không lưu mốc neo (anchor) duy nhất ở các file làm việc dễ bị xóa.
  Sử dụng cơ chế **Git Reference bất biến nội bộ** (`refs/gates/<task_id>/a`):
  ```bash
  git update-ref refs/gates/<task_id>/a <base_commit_sha>
  ```
  Khi Gate A chạy, kiểm tra `git rev-parse --verify refs/gates/<task_id>/a`. Nếu ref đã tồn tại -> lập tức `REJECT` ("Gate A already passed for task (chain reset forbidden)").
  Worker có xóa sạch file trên đĩa thì Git ref vẫn tồn tại trong database `.git/refs`, ngăn chặn vĩnh viễn việc tua ngược hoặc dịch chuyển base commit.

---

## 2. Cấu Hình Bắt Buộc Khi Điều Phối Claude Reviewer (Windows Farm Environment)
* **Thời gian chạy test:** Trên Windows, các test suite tích hợp git/CLI (50-60 tests) thường mất 40-50 giây cho mỗi lượt chạy pytest.
* **Nguy cơ cạn turn / timeout:** Mặc định `claude_worker.py --role reviewer` chỉ cấp `default_turns: 8` và nếu Coordinator để timeout ngắn (100-150s), Reviewer sẽ bị timeout hoặc `Error: Reached max turns (8)` trước khi kịp hoàn thành phân tích diff và chạy probe.
* **Cấu hình chuẩn hóa khi gọi Reviewer:**
  ```bash
  python D:/Taadaa/tools/claude_worker.py --role reviewer --max-turns 15 --timeout 300 "<prompt>"
  ```
  Cấp đủ tối thiểu 15 turns và 300s để Reviewer có không gian chạy pytest và probe bảo mật an toàn.

---

## 3. Kỷ Luật Trình Bày Telegram — Tuyệt Đối Cấm LaTeX Math Syntax
* **Triệu chứng lỗi:** Sử dụng cú pháp LaTeX math như `$$\text{...} \longrightarrow ...$$` hoặc `$\rightarrow$` trên nền tảng Telegram. Telegram không hỗ trợ MathJax/LaTeX renderer, dẫn tới việc tin nhắn bị bung ra mã thô đầy dấu gạch chéo ngược (`\text{...}`, `\longrightarrow`), gây ức chế cho người dùng.
* **Quy chuẩn bất biến:**
  - 100% dùng ký tự Unicode chuẩn: `→`, `←`, `⇒`, `⇔`.
  - Hoặc dùng dấu text thuần: `->`, `<-`, `=>`.
  - Tuyệt đối không bọc công thức luồng trong thẻ toán học `$$` hoặc `$`.
