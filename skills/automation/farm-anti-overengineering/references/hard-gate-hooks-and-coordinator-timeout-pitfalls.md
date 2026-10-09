# Hard Gate Hooks & Coordinator Timeout Pitfalls (09/09/2026)

Nguồn: Phân tích sự cố xử lý 1 tiếng (Reg TikTok Pipeline alert) — Claude Opus CLI audit.

---

## 1. Hai lỗi timeout 900s làm mất 30 phút (bài học trực tiếp)

### Pitfall A — `read_file` trên file log > 10MB

**Triệu chứng:** Coordinator dùng `read_file("D:/Taadaa/Tiktok_Reg/social_reg_log.txt")` trên file 215MB.
Tool cố load full vào memory + đếm dòng → kẹt cứng 900s (15 phút).

**Rule cứng:** Trước bất kỳ read_file nào trên file log, BẮT BUỘC kiểm tra size trước:
```bash
ls -lh D:/Taadaa/Tiktok_Reg/social_reg_log.txt
```
Nếu > 10MB: BẮT BUỘC dùng một trong các lệnh sau:
```bash
tail -n 200 D:/Taadaa/Tiktok_Reg/social_reg_log.txt
grep -m 50 "PATTERN" D:/Taadaa/Tiktok_Reg/social_reg_log.txt
# hoặc
read_file(path, offset=<total_lines - 200>, limit=200)
```

### Pitfall B — `pytest tests/` quét toàn bộ repo

**Triệu chứng:** Sau khi worker sửa xong code, Coordinator chạy `pytest D:/Taadaa/Tiktok_Reg/tests/` thay vì focused test.
Trong suite có test giả lập subprocess dài → kẹt 900s (15 phút) thêm.

**Rule cứng:** Sau dispatch worker, BẮT BUỘC chỉ chạy đúng file test liên quan đến patch:
```bash
D:/Taadaa/python-envs/automation/Scripts/python.exe -m pytest \
  D:/Taadaa/Tiktok_Reg/tests/test_detect_after_continue.py -x -q
```
Kết quả xanh trong < 30s. KHÔNG BAO GIỜ `pytest tests/` hoặc `pytest .`.

---

## 2. Dispatch Loop thất bại 4-5 lượt — nguyên nhân và fix

**Triệu chứng:** Worker dispatch 4-5 lần: lượt 1&2 sa vào phân tích/lập kế hoạch (analysis paralysis), lượt 3&4 vướng `autouse` fixture mock và ambiguous header trong openpyxl.

**Nguyên nhân gốc Coordinator:**
- Prompt không đóng gói diff/hướng dẫn cụ thể → worker phải tự mò.
- Coordinator không rà soát test environment trước dispatch (fixture mock sẵn có thể conflict).

**Checklist dispatch chuẩn (bắt buộc):**
1. Đọc file test target trước: kiểm tra `autouse` fixtures, mock conflicts.
2. Prompt Worker PHẢI chứa đủ 3 block:
   - `FILE: D:\Taadaa\...\file.py` (đường dẫn tuyệt đối)
   - `SCOPE: <mô tả hàm/class cần sửa, giới hạn rõ>`
   - `FOCUSED_TEST: <lệnh pytest đúng 1 file>`
3. Budget Worker: tối đa 15 tool calls, 15 phút.

---

## 3. Hard Gate Hooks — Cơ chế cứng enforcement (mới 09/09/2026)

Soft prompt không đủ — context loãng sau 50k token, agent panic bypass rule mềm.
Giải pháp: **PreToolUse hook** ở tầng Hermes — block TRƯỚC KHI tool thực thi.

### Cấu hình active tại `~/.hermes/config.yaml`:
```yaml
hooks:
  pre_tool_call:
    - matcher: read_file
      command: "python C:/Users/Kibe/AppData/Local/hermes/hooks/guard_read_file_size.py"
      timeout: 5
    - matcher: terminal
      command: "python C:/Users/Kibe/AppData/Local/hermes/hooks/guard_pytest_scope.py"
      timeout: 5
    - matcher: delegate_task
      command: "python C:/Users/Kibe/AppData/Local/hermes/hooks/guard_dispatch_contract.py"
      timeout: 5
```

### Ba hook scripts tại `C:/Users/Kibe/AppData/Local/hermes/hooks/`:

**guard_read_file_size.py** — Block `read_file` trên file > 10MB:
```python
import json, sys, os
MAX = 10 * 1024 * 1024
payload = json.load(sys.stdin)
path = (payload.get("args") or {}).get("path") or ""
if path:
    try:
        size = os.path.getsize(path)
        if size > MAX:
            mb = size // 1024 // 1024
            print(json.dumps({"action": "block", "message":
                f"[HARD GATE] read_file CHẶN: {mb}MB > 10MB. Dùng tail -n 200 hoặc grep."}))
    except OSError:
        pass
```

**guard_pytest_scope.py** — Block pytest không có specific file path:
```python
import json, sys, re
payload = json.load(sys.stdin)
cmd = (payload.get("args") or {}).get("command") or ""
if re.search(r'\bpytest\b', cmd):
    has_file = re.search(r'pytest[^\n]*[\s/\\][^\s]+test[^\s]*\.py', cmd)
    has_k = re.search(r'\s-k\s+\S', cmd)
    if not has_file and not has_k:
        print(json.dumps({"action": "block", "message":
            "[HARD GATE] pytest CHẶN: CẤM quét toàn repo. BẮT BUỘC chỉ định file cụ thể."}))
```

**guard_dispatch_contract.py** — Block delegate_task thiếu 3 block bắt buộc:
```python
import json, sys
REQUIRED = ["FILE:", "SCOPE:", "FOCUSED_TEST:"]
payload = json.load(sys.stdin)
args = payload.get("args") or {}
combined = (args.get("goal") or "") + "\n" + (args.get("context") or "")
if combined.strip():
    missing = [t for t in REQUIRED if t not in combined]
    if missing or len(combined.strip()) < 150:
        print(json.dumps({"action": "block", "message":
            f"[HARD GATE] delegate_task CHẶN. Thiếu: {missing}. Điền đủ FILE:/SCOPE:/FOCUSED_TEST:."}))
```

### Allowlist hooks (bắt buộc sau khi thêm config):
```bash
hermes --accept-hooks chat -q "echo hi"
hermes hooks doctor   # All 3 phải ✓ allowlisted
```

### Revert nếu cần:
```bash
hermes hooks revoke "python C:/Users/Kibe/AppData/Local/hermes/hooks/guard_read_file_size.py"
hermes hooks revoke "python C:/Users/Kibe/AppData/Local/hermes/hooks/guard_pytest_scope.py"
hermes hooks revoke "python C:/Users/Kibe/AppData/Local/hermes/hooks/guard_dispatch_contract.py"
hermes config set terminal.timeout 900
# Xóa block hooks: trong config.yaml
```

---

## 4. Vì sao soft prompt LUÔN thất bại (Claude Opus audit verdict)

- **Prompt là dữ liệu, không phải luật:** Sau 50k token, attention decay làm loãng tín hiệu rule.
- **Panic collapse:** Khi gặp lỗi lặp, model bỏ qua ràng buộc mềm để làm "bất kỳ thứ gì" pass.
- **Không deny ở tầng thực thi:** Nói "đừng làm X" nhưng không có gì từ chối khi nó vẫn gọi tool.
- **Nguyên tắc:** *Cái gì không được làm → REJECT ở tầng PreToolUse hook, không phải nhắc ở prompt.*

---

## 5. Bài học Root Cause — Reg TikTok Pipeline Alert (09/09/2026)

Vì Coordinator mất hơn 1 tiếng cho 1 fix 5 phút do vi phạm đồng thời 4 rule:
1. read_file 215MB → 15 phút chết
2. pytest tests/ → 15 phút chết  
3. Dispatch prompt rỗng → 4-5 lượt worker
4. Không pre-recon test environment → worker vướng fixture conflict

Claude Opus phán quyết: "Không một phút nào trong đó là do bài toán khó."

---

## 6. Worker Subagent Budget Exhaustion — Analysis Paralysis on Pre-specified Tests (19/09/2026)

**Triệu chứng:** Worker được dispatch với budget hẹp (ví dụ <= 10 calls, 5 phút, scope lock 1 file test), yêu cầu viết 1 unit test đã có sẵn đặc tả cụ thể (tên test, input condition, expected behavior).
Thay vì clone pattern từ test liền kề trong target test file rồi patch và run pytest ngay (hoàn thành trong 3-4 calls), Worker lại đi đọc sâu mã nguồn implementation (dùng search_files, grep, đọc qua nhiều offset của flow file). Hậu quả: chạm trần max tool-calling iterations trước khi kịp patch hay chạy test.

**Quy tắc thực thi cho Worker (Test-writing under tight budget):**
1. **Pattern from adjacent test:** Đọc đúng ~30-50 dòng của test tương tự liền kề trong target test file (ví dụ `test_upload_hook_gate5_video_not_rendered`). KHÔNG mở đọc mã production khi requirement đã chỉ rõ input/output.
2. **Patch ngay ở Call 2:** Dùng `patch` đưa test mới vào ngay sau test tương tự.
3. **Run focused verification ở Call 3:** Chạy đúng lệnh pytest focused (`pytest <target_file> -k "<test_name>"`).
4. **Báo cáo kết quả và kết thúc:** Không mở thêm bất kỳ file nào khác nếu test đã pass.

---

## 7. Worker Subagent Truncation vs Wrapper/Decorator Pattern (19/09/2026)

**Triệu chứng:** Worker subagent nhận yêu cầu chèn telemetry/observability vào module lớn (500+ dòng) có nhiều điểm return (`return { ... }` rải rác 10+ vị trí khác nhau). Worker cố gắng thay thế toàn bộ các khối return hoặc viết lại toàn bộ hàm -> chạm trần generation tokens và gây lỗi: `status=failed: Response remained truncated after 4 continuation attempts`.

**Root Cause:**
- Thay đổi 10+ return statements riêng lẻ trong 1 file lớn đòi hỏi diff/replace payload quá dài, làm cạn context output của LLM worker.
- Worker sa vào việc lặp lại mã nguồn nhiều lần trong output generation dẫn đến loop truncation.

**Quy tắc bất biến (Wrapper/Decorator pattern cho Telemetry & Return Payloads):**
1. **Dùng Outer Wrapper thay vì sửa N return statements:**
   - Đổi tên hàm implementation ban đầu thành `_func_impl(...)`.
   - Viết một hàm wrapper ngắn gọn `func(...)`:
     ```python
     def func(*args, **kwargs):
         start_t = time.time()
         logger.info(f"Bắt đầu thực thi {args}...")
         res = _func_impl(*args, **kwargs)
         duration = round(time.time() - start_t, 2)
         res["telemetry"] = {
             "step_timings": res.get("step_timings", {}),
             "duration_s": duration,
             "status": res.get("status", "UNKNOWN"),
             "reason_code": res.get("reason_code", "UNKNOWN")
         }
         if res.get("success"):
             logger.info(f"SUCCESS: {res.get('status')} ({duration}s)")
         else:
             logger.warning(f"FAIL: {res.get('status')} ({res.get('reason_code')}, {duration}s)")
         return res
     ```
2. **Ưu điểm vượt trội:**
   - Tiết kiệm 90% diff payload: Không cần chạm vào bất kỳ dòng return nào bên trong hàm implementation.
   - Zero-regression: Mọi logic return bên trong giữ nguyên 100%, payload telemetry được gắn đồng nhất ở một điểm duy nhất (single point of return).
   - Worker hoàn thành chỉ trong 1-2 calls mà không bao giờ bị dính truncation.

