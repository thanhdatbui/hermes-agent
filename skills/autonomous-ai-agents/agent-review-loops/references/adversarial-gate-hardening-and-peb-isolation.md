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

---

## 4. Quét RAM Tiến Trình Cha & Khắc Phục Bằng Windows Process DACL
* **Cơ chế tấn công:**
  Dù đã dùng `SetEnvironmentVariableW(..., None)` xóa sạch biến môi trường khỏi PEB, chuỗi secret vẫn có thể còn nằm trong vùng nhớ heap/cache của Python runtime ở tiến trình cha (Gate).
  Tiến trình con (worker script được gọi trong cmd claim / acceptance test) chạy cùng Windows User có thể dùng `OpenProcess(0x0410, False, parent_pid)` (với cờ `PROCESS_QUERY_INFORMATION | PROCESS_VM_READ`) và dùng `ReadProcessMemory` quét toàn bộ trang nhớ heap của cha để bóc tách secret.
* **Biện pháp khắc phục qua Process DACL:**
  Ngay khi tiến trình Gate khởi động, áp dụng DACL hạn chế quyền truy cập lên chính process handle:
  ```python
  import win32api, win32security
  h_proc = win32api.GetCurrentProcess()
  token = win32security.OpenProcessToken(h_proc, win32security.TOKEN_QUERY)
  user_sid = win32security.GetTokenInformation(token, win32security.TokenUser)[0]

  new_dacl = win32security.ACL()
  # Chặn đọc/ghi bộ nhớ và chặn thay đổi DACL từ tiến trình cùng user:
  deny_mask = 0x0010 | 0x0020 | 0x0008 | 0x00040000 | 0x00080000
  new_dacl.AddAccessDeniedAce(win32security.ACL_REVISION, deny_mask, user_sid)
  allow_mask = 0x13FFEF # Loại bỏ hoàn toàn WRITE_DAC và WRITE_OWNER
  new_dacl.AddAccessAllowedAce(win32security.ACL_REVISION, allow_mask, user_sid)

  win32security.SetSecurityInfo(
      h_proc, win32security.SE_KERNEL_OBJECT, win32security.DACL_SECURITY_INFORMATION,
      None, None, new_dacl, None
  )
  ```
  Khi đó, mọi lệnh `OpenProcess(PROCESS_VM_READ)` từ con đều bị kernel Windows trả về `ERROR_ACCESS_DENIED (5)`.

---

## 5. Tấn Công Xóa Git Ref & Phân Định Ranh Giới Tin Cậy (Trust Boundary Scope)
* **Kỹ thuật tấn công xóa ref:**
  Nếu anchor duy nhất lưu ở `refs/gates/<task_id>/a`, worker trong repo có thể chạy `git update-ref -d refs/gates/<task_id>/a` kết hợp xóa file receipts/ledger để reset chuỗi.
* **Phòng thủ sâu (Defense in Depth):**
  Lưu bản sao ledger tại thư mục an toàn ngoài working tree của repository (`%TEMP%/.hermes_gates_coord/` hoặc `COORDINATOR_STATE_DIR`). Khi đọc ledger, gate đối soát song song cả local ledger và coordinator anchor ledger.
* **Đặc tả ranh giới tin cậy (Security Model Invariant):**
  - **Bản chất Gate:** Là cơ chế bảo đảm kỷ luật kỹ thuật (mechanical development guardrails) chống worker sửa sai scope, commit bừa bãi, skip test, hoặc vô tình/cố ý tamper file receipts.
  - **Ranh giới OS Sandbox:** Hai tiến trình chạy dưới cùng một Windows User Account không bao giờ tạo thành một hypervisor sandbox tuyệt đối. Việc cách ly hoàn toàn mã độc thù địch (hostile adversary isolation) bắt buộc phải do môi trường host đảm nhiệm (Job Object Low Integrity, AppContainer, hoặc User riêng).
  - Phải ghi rõ Threat Model trong docstring của Gate để tránh rơi vào vòng lặp review tranh cãi vô hạn về quyền hạn cùng user.

---

## 6. Xử Lý Phán Quyết APPROVED_WITH_CONDITIONS & Kỹ Thuật Đóng Review Loop (Round 10-11 Lessons)
* **Quy tắc phân tách ranh giới kiểm thử (Cooperative vs Hostile):**
  - Không được đặt tên test gây ngộ nhận về khả năng chống lại tấn công cùng quyền user (ví dụ: đổi `test_deletion_attack_to_reset_chain_blocked` thành `test_cooperative_deletion_attack_to_reset_chain_blocked`).
  - Sử dụng `@pytest.mark.xfail(strict=True, reason="...")` để minh chứng ranh giới kiến trúc đã biết (known architectural boundary) ngay trong test suite mà không làm gãy pipeline kiểm thử (giữ 100% test green).
* **Gộp Ledger Đa Nguồn (Ledger Union Pattern):**
  - Trong `read_gate_ledger`, không chỉ dùng fallback khi file local mất (vì file local có thể bị cắt về rỗng `0 bytes`). Bắt buộc đọc và gộp (union) toàn bộ bản ghi hợp lệ từ cả local ledger và coordinator anchor ledger ngoài repo, xác thực canonical HMAC trên từng dòng.
* **Fail-Closed Sớm Tại Gate Đầu (Gate A Ref Anchoring):**
  - Kiểm tra giá trị trả về của `set_gate_a_git_ref`. Nếu không ghi được ref vào `.git/refs/gates/<task_id>/a`, Gate A phải lập tức trả về `(False, ...)` thay vì trả PASS rồi để Gate B fail muộn.
* **Kỷ luật "Cấm khóc lóc blocked khi làm việc":**
  - Khi Reviewer đưa ra các phát hiện về ranh giới kiến trúc hệ thống (như same-user process isolation), Coordinator không tranh cãi hay viện cớ để đóng băng task. Ngay lập tức chuẩn hóa docstring Security Architecture & Threat Model, cập nhật test suite khớp đúng phạm vi thực tế để đưa Reviewer từ `APPROVED_WITH_CONDITIONS` lên `APPROVED` trọn vẹn.
