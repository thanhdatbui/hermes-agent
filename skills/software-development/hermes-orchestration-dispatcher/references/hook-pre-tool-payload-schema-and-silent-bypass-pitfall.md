# Pre-Tool Hook Payload Schema, Silent Bypass Pitfall & Hard Enforcement

## 1. Hermes Pre-Tool Hook Payload Contract

Khi Hermes kích hoạt `pre_tool_call` hooks (cấu hình trong `config.yaml` dưới `hooks.pre_tool_call`), payload JSON được truyền qua `stdin` có schema chuẩn:
```json
{
  "tool_name": "delegate_task",
  "tool_input": {
    "goal": "...",
    "context": "..."
  }
}
```

### 🛑 Pitfall Cốt Tử: Silent Bypass do đọc sai key `tool_input`
- **Nguyên nhân bug:** Nhiều script hook cũ (như `D:/Taadaa/tools/hooks/guard_dispatch_contract.py`) đọc payload theo định dạng `args = payload.get("args") or {}`.
- **Hậu quả:** `args` nhận giá trị rỗng `{}` $\to$ `goal = ""` $\to$ `if not goal.strip(): sys.exit(0)`. Hook thoát êm với exit code 0 mà không thẩm định bất kỳ nội dung nào! 100% các lệnh `delegate_task` vi phạm (thiếu contract, goal mở, thiếu test) đều lọt qua mà không bị chặn.
- **Quy tắc giải mã bắt buộc (Fail-Closed & Symmetrical Parsing):**
```python
tool_name = payload.get("tool_name") or payload.get("tool") or ""
args = payload.get("tool_input") or payload.get("args") or {}
if isinstance(args, str):
    try:
        args = json.loads(args)
    except Exception:
        pass
if not isinstance(args, dict):
    print(json.dumps({"action": "block", "message": "[FAIL-CLOSED] tool_input must be valid dict"}))
    sys.exit(0)
```

---

## 2. Phòng Chống "Rogue Editing" của Coordinator (Đảo lộn vai trò Coordinator vs Worker)

### Triệu chứng vi phạm:
Khi gặp áp lực hoàn thành task (Farm alert, reviewer từ chối điểm), Coordinator thường có phản xạ tự gọi `patch` hoặc `write_file` trực tiếp trong session chính, sau đó tự commit `[L2-surgery]` trên nhiều repo cùng lúc TRƯỚC KHI dispatch Worker.

### Kỷ luật cưỡng chế:
1. **L2 Emergency Surgery KHÔNG PHẢI lối tắt đi tắt đón đầu:**
   - L2 CHỈ được kích hoạt khi: (a) TRANSIENT retry đủ 2 lần vẫn timeout HOẶC (b) STRUCTURAL failure lần 2 từ Worker.
   - CẤM TUYỆT ĐỐI tự xưng `[L2-surgery]` khi chưa hề có Worker nào chạy hoặc thất bại.
2. **Ngân sách O(1) của L2 là bất khả xâm phạm:**
   - Tối đa $\le 2$ files (tính cả file test).
   - Tối đa $\le 30$ dòng diff (`git diff --numstat` trước khi commit).
   - DUY NHẤT 1 lần L2 cho toàn bộ session.
3. **Mọi can thiệp code thông thường (T2) BẮT BUỘC dispatch Worker:**
   - Coordinator chỉ chuẩn bị bản vẽ, tìm anchor duy nhất O(1), cấp Patch Contract và dispatch qua `delegate_task`.

---

## 3. Quy Chuẩn Bắt Buộc Khi Dispatch Worker (Gate 2 & Gate 4)

Để triệt tiêu tình trạng Worker vượt quá budget 15 calls và bị timeout 480s:
1. **Gate 2 (Patch Contract O(1)):**
   - CẤM dispatch goal mở ("sửa file X theo nhận xét Reviewer").
   - BẮT BUỘC cung cấp: `FILE:`, `OLD_STRING:`, `NEW_STRING:`, `FOCUSED_TEST: <lệnh_test_offline < 30s>`.
2. **Gate 4 (Fail-Fast Injection):**
   - BẮT BUỘC tiêm vào prompt: `"NẾU trong <= 3 iterations đầu nhận thấy scope bất khả thi với budget 15 calls thì PHẢI DỪNG NGAY (ABORT) và trả về anchor + proposed contract, cấm đốt hết budget để mò file rồi fail im lặng."`

---

## 4. Kỷ Luật Terminal Foreground Timeout (`GUARD_FOREGROUND_TIMEOUT_EXCEEDED`)

- Hệ thống bảo vệ giới hạn nghiêm ngặt timeout lệnh foreground: `timeout <= 60s`. Lệnh đặt timeout 90s - 300s sẽ bị guard chặn đứng ngay.
- Đối với các tác vụ CLI cần thời gian suy nghĩ dài (> 30s) như `claude -p` trên prompt lớn:
  * BẮT BUỘC chạy chế độ nền: `terminal(command="claude -p ... > output.txt 2>&1", background=True, notify_on_complete=True, timeout=300)`.
