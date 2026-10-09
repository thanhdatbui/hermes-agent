# Coordinator Paralysis Recovery & Two-Tier Guard Model

## Bối cảnh sự cố (01/10 – 05/10/2026)
Hệ thống điều phối Phone Farm rơi vào trạng thái tê liệt hoàn toàn (Coordinator Paralysis) khi các lớp bảo vệ (guard/hook) chồng chéo lên nhau tạo thành **bẫy khóa chết hai chiều (Deadlock tuyệt đối)**:
1. **Self-Protection Blacklist:** Hook `_on_pre_tool_call` chặn đứng mọi tool call (`patch`, `write_file`, `terminal`) nếu tham số có nhắc tới thư mục hook/guard/config.
2. **Default-Deny Terminal Gate:** Chặn các lệnh chẩn đoán, và regex bắt `git.*push` bị false-positive bắt dính cả chuỗi text nằm trong tham số của CLI ngoài (ví dụ `claude -p "..."`).
3. **Write Ledger T1 <= 15 dòng:** Coordinator bị tước quyền sửa file trong session chính khi đã dùng hết ngân sách 15 dòng.
4. **Mandatory Sol Plan:** Mọi task sửa code (`TASK_KIND: EDIT`) bị ép buộc phải có `SOL_PLAN_ID`, nếu thiếu thì tự gọi Sol rồi vẫn chặn bắt dispatch lại.
5. **Rate-limit của công cụ cứu hộ duy nhất:** Khi Claude CLI hết quota (session limit resets), Coordinator bên trong hoàn toàn không còn bất kỳ đường nào để can thiệp.

---

## 1. Nguyên tắc cốt lõi: Phân định 2 Tầng Guard (Two-Tier Guard Model)

Để đảm bảo vừa an toàn tuyệt đối cho thiết bị vừa không trói tay Coordinator:

### TẦNG 1: CHẶN CỨNG BẢO VỆ TÀI SẢN (FAIL-CLOSED, ZERO-BYPASS)
Chỉ áp dụng cho các hành vi xâm phạm tài sản vật lý hoặc phá hoại hệ thống. Nhẹ, chạy local, độc lập hoàn toàn với mạng/LLM:
- **Tài sản nick & tài khoản:** Chặn tuyệt đối xóa/logout nick (`FARM-ASSET-001`, `do_logout_account.py`).
- **Phần cứng thiết bị:** Chặn tuyệt đối ADB bấm tay (`adb shell input tap/swipe/keyevent`) thay cho sửa code.
- **Tài nguyên đĩa:** Chặn tuyệt đối quét đĩa diện rộng (`os.walk`, `rglob`, `grep -rn`, `find` trên toàn bộ ổ `D:/Taadaa`).
- **Phá hoại Git:** Chặn tuyệt đối `git push --force`, `git reset --hard`, `git checkout .`.

### TẦNG 2: GIÁM SÁT QUY TRÌNH & ĐIỀU PHỐI (WARN-ONLY, LOG-FIRST, CẤM BLOCK TÊ LIỆT)
Không được dùng để chặn cứng Coordinator giữa phiên làm việc:
- **Sol Planning:** Chỉ mang tính tư vấn kiến trúc cho task rủi ro cao (high-risk $\ge 3$ files, schema, auth). **Routine Code Surgery O(1)** (có `FILE:`, `OLD_STRING:`, `NEW_STRING:`, `FOCUSED_TEST:`, `anchor count == 1`) BẮT BUỘC ĐƯỢC CHẠY NGAY, không bao giờ chặn vì thiếu Sol Plan.
- **Trần Dispatch & Write Ledger:** Ghi nhật ký audit/telemetry để hậu kiểm (`closeout_gate.py`), không được chặn đứng công việc giữa phiên.
- **Dịch vụ phụ thuộc bên ngoài:** Khi Sol, 9Router, hoặc Claude CLI offline/timeout/rate-limit, hệ thống **BẮT BUỘC PHẢI FAIL-OPEN (cho phép tiếp tục)** kèm cảnh báo, tuyệt đối không được block dây chuyền.
- **Closeout Gate:** Chỉ kích hoạt khi User ra lệnh chốt phiên để push remote, không dùng để cản trở các thao tác sửa chữa, chạy test giữa phiên.

---

## 2. Kỹ thuật chống False-Positive trong Guard Hooks

### Tránh quét Regex trên toàn bộ chuỗi command
- **Sai:** `re.search(r"\bgit\b.*\bpush\b", cmd)` $\to$ Sẽ chặn oan các lệnh như `claude -p "Review git diff and do not push"`.
- **Đúng:** Tách từng segment lệnh theo `&&`, `;`, `|`, bỏ qua nội dung nằm trong dấu nháy (`"` hoặc `'`). Chỉ kiểm tra subcommand git ở vị trí đầu của lệnh:
  ```python
  git_m = re.match(r"^git(?:\.exe)?(?:\s+-[^\s]+)*\s+push\b", seg, re.IGNORECASE)
  ```

### Miễn trừ Self-Protection cho các CLI bảo trì
Khi Coordinator chạy các CLI bảo trì được cấp phép (`claude`, `opencode`, `antigravity`), hook Self-Protection không được chặn chỉ vì tham số dòng lệnh có chứa đường dẫn file hook/guard cần sửa:
```python
is_allowed_cli = bool(re.match(r"^(?:claude\b|opencode\b|antigravity\b)", c_strip, re.IGNORECASE))
if not is_allowed_cli:
    # Mới duyệt kiểm tra _is_protected_target
```

---

## 3. Cửa thoát hiểm khẩn cấp khi Session bị Deadlock (Escape Hatch)

Khi một phiên làm việc bị chính guard nội bộ khóa cứng (không thể `patch`, `write_file`, hay gõ `terminal`):
- **CẤM:** Cố gắng gõ đi gõ lại các tool nội bộ trong vô vọng.
- **BẮT BUỘC:** Cung cấp ngay lệnh 1-click cho User chạy ngoài host PowerShell (vì host nằm ngoài sandbox hook của Hermes):
  ```powershell
  (Get-Content "$env:LOCALAPPDATA\hermes\config.yaml") -replace '- farm-coordinator-guard', '' | Set-Content "$env:LOCALAPPDATA\hermes\config.yaml"
  ```
- **Kỷ luật gửi prompt/nội dung dài qua Telegram:** Trên giao diện Telegram mobile, User không thể copy các khối text quá dài mà không bị vỡ. Bắt buộc:
  1. Ghi nội dung vào file tạm trên đĩa (`write_file` ra `~/*.txt`) để User mở đọc trực tiếp.
  2. Hoặc chia nhỏ thành các phần rõ ràng (`PHẦN 1/N`, `PHẦN 2/N`) ngắn gọn để copy không lỗi.
