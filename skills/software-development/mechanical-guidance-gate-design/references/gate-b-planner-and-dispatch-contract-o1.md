# Gate B Planner Architecture (Gemini Web with Claude CLI Fallback) & Dispatch Contract O(1)

## 1. Bối cảnh & Lý do hình thành
- Trước đây, Coordinator (Gemini Flash) thường tự suy nghĩ plan sửa code rồi tự ý dispatch Worker hoặc tự sửa file. Do chất lượng reasoning của Flash ở các bài toán kiến trúc còn hạn chế, các chỉ dẫn cho Worker thường thiếu chính xác, gây ra việc Worker mò mẫm hoặc làm hỏng logic.
- Ngoài ra, các phiên bản Gate cũ từng bị over-engineering (1.700 dòng code HMAC, Windows DACL, memory scan) dẫn đến script tự treo > 120s gây tê liệt (paralysis).
- Giải pháp: Chuẩn hóa Gate B thành một script Python tinh gọn (`gate_b_planner.py`), chạy nhanh (<15s), tận dụng sức mạnh reasoning của `gemini-web` (Argon 4 Pool) và tự động fallback sang `claude -p` (Claude CLI local).

## 2. Kiến trúc Fallback Hai Tầng của Gate B

```
                     [BÀI TOÁN SỬA CODE / FIX BUG]
                                  │
                                  ▼
               ┌─────────────────────────────────────┐
               │    Tier 1: gemini-web (:20129)       │
               │    - Argon 4 Web Pool (15 Pro accs)  │
               │    - Hard timeout: 15s (curl wall)  │
               │    - Tốn 0 token Claude             │
               └──────────────────┬──────────────────┘
                                  │
                  Timeout >15s / 401 / Parse Fail
                                  │
                                  ▼
               ┌─────────────────────────────────────┐
               │    Tier 2: claude -p (CLI Local)    │
               │    - Claude Sonnet/Haiku local      │
               │    - Thuần text (--tools "")        │
               │    - Hard timeout: 60s              │
               └──────────────────┬──────────────────┘
                                  │
                                  ▼
               ┌─────────────────────────────────────┐
               │         VALIDATE & CONTRACT O(1)    │
               │  - txt.count(old_string) == 1       │
               │  - Tính file_sha256                 │
               │  - Xuất JSON chuẩn cho Worker       │
               └─────────────────────────────────────┘
```

## 3. Script Mẫu Chuẩn: `gate_b_planner.py`

```python
import sys, json, re, subprocess, hashlib, shutil
from pathlib import Path

ROOT = Path(sys.argv[2] if len(sys.argv) > 2 else ".").resolve()
TASK = sys.argv[1]
KEYS = ("target_file", "old_string", "new_string", "test_cmd")
SYS = ("Return ONLY one JSON object with keys target_file (relative path), old_string "
       "(exact, unique in file), new_string, test_cmd. No prose, no markdown.")

def ask_gemini(prompt):  # hard 15s wall-clock
    body = json.dumps({"model": "gemini-web", "messages": [
        {"role": "system", "content": SYS}, {"role": "user", "content": prompt}]})
    r = subprocess.run(["curl", "-sS", "--max-time", "15", "-H", "Content-Type: application/json",
        "-d", body, "http://127.0.0.1:20129/v1/chat/completions"],
        capture_output=True, text=True, timeout=17)
    if r.returncode: raise RuntimeError(r.stderr)
    return json.loads(r.stdout)["choices"][0]["message"]["content"]

def ask_claude(prompt):
    r = subprocess.run([shutil.which("claude"), "-p", "--tools", "", "--no-session-persistence",
        "--append-system-prompt", SYS], input=prompt, capture_output=True, text=True, timeout=60)
    if r.returncode: raise RuntimeError(r.stderr)
    return r.stdout

def validate(raw):  # fail-closed: mọi thứ sai -> raise để chuyển fallback
    m = re.search(r"\{.*\}", raw, re.S)
    if not m: raise ValueError("no json found")
    c = json.loads(m.group(0))
    if not all(isinstance(c.get(k), str) and c[k].strip() for k in KEYS): raise ValueError("missing key")
    f = (ROOT / c["target_file"]).resolve()
    if ROOT not in f.parents or not f.is_file(): raise ValueError("bad target_file")
    txt = f.read_text(encoding="utf-8")
    if txt.count(c["old_string"]) != 1: raise ValueError("old_string not unique/absent")
    if c["old_string"] == c["new_string"]: raise ValueError("noop patch")
    c["file_sha256"] = hashlib.sha256(txt.encode()).hexdigest()
    return c

def main():
    for name, fn in (("gemini-web", ask_gemini), ("claude-cli", ask_claude)):
        try:
            c = validate(fn(TASK))
            c["planner"] = name
            print(json.dumps(c, ensure_ascii=False))
            return 0
        except Exception as e:
            print(f"[gate_b] {name} failed: {e}", file=sys.stderr)
    print(json.dumps({"status": "REJECTED", "reason": "all planners failed"}))
    return 2

if __name__ == "__main__":
    sys.exit(main())
```

## 4. Quy định Thực thi tại Gate C (Worker Execution)
Khi Worker (Sol T1 / Agy T2 / Haiku T3) nhận Contract từ Gate B, cấm Worker tự suy diễn hoặc dùng lệnh regex/sed/awk phức tạp:
1. **Kiểm tra tính toàn vẹn (Integrity Check):** Tính `sha256` của `target_file`. Nếu không khớp `file_sha256` trong contract $\rightarrow$ Dừng ngay, báo `STATE_DRIFT`.
2. **Thay thế chuỗi duy nhất O(1):** Tìm đúng `old_string` và thay bằng `new_string` đúng 1 lần duy nhất.
3. **Chạy test tập trung:** Thực thi `test_cmd`. Exit code 0 mới coi là PASS.
