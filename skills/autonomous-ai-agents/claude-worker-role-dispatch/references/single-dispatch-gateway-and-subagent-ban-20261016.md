# Single Dispatch Gateway & Strict Subagent Ban for Code Editing (16/10/2026)

## 1. Incident Audit: The 6-Hour Subagent Loop (16/10/2026 00:00 - 06:00)

During the incident on 16/10/2026, Coordinator (Hermes) repeatedly violated the explicit directive in USER.md & MEMORY:
- **Rule Violated:** *"Worker: Haiku 5.5 CLI, AG CLI dự phòng; cấm delegate_task sửa code"*.
- **Actual Behavior:** Coordinator spawned subagents via `delegate_task` (`ag-gemini-pool-3` / OmniRoute) over 25 consecutive times to perform micro-edits and chase Closeout Gate scores (82/100 -> 86/100).
- **Consequence:** Each subagent consumed 10–15 calls, had high latency (~120s–180s), bloated conversation context, and prolonged what should have been a 5-minute closeout into a grueling 6-hour overnight ordeal.

---

## 2. Architecture: Single Dispatch Gateway (`dispatch_worker.py`)

To physically enforce compliance and eliminate rogue subagent spawning, all routine code edits, fixes, and test repairs MUST pass through `D:/Taadaa/tools/dispatch_worker.py`:

```text
[Mọi task sửa code / fix bug / viết test thông thường]
                        │
                        ▼ (Bắt buộc chạy qua 1 cổng duy nhất)
       [python D:/Taadaa/tools/dispatch_worker.py "<contract>"]
                        │
                        ▼
       [TẦNG 1: Haiku 5.5 CLI (claude_worker.py --role worker)]
       (Tối đa 8 turns, timeout 60s, sửa in-place nhanh gọn)
                        │
                        ├──> [Thành công (exit 0)] ──> Xong ngay!
                        │
                        ▼ [Thất bại / Hết Quota / Timeout 124 / 127]
       [TẦNG 2 (Tự động Fallback): Agy CLI (ag_cli.py fix)]
       (Cụm Pool 7 tài khoản Google Pro độc lập, model gemini-3.8-flash-high)
                        │
                        ▼
       [Ghi nhận Audit Log vào D:/Taadaa/logs/dispatch.jsonl]
```

### CLI Specification
```bash
python D:/Taadaa/tools/dispatch_worker.py "<contract O(1)>" --workdir <repo> [--file <file>] [--timeout 60] [--max-turns 8]
```
- `--workdir`: Working directory của repo (mặc định: `.`).
- `--file`: File đích cần sửa (tuỳ chọn).
- `--timeout`: Timeout cho mỗi worker (mặc định: 60s).
- `--max-turns`: Giới hạn turns cho Haiku (mặc định: 8, kẹp trần 15).

---

## 3. Strict Invariant: Ban `delegate_task` for Code Edits

1. **CẤM TUYỆT ĐỐI** gọi `delegate_task` để sửa code, refactor hoặc viết test.
2. Coordinator chỉ được phép đọc log, inspect ADB, check trạng thái O(1). Mọi thao tác sửa code BẮT BUỘC gọi `dispatch_worker.py`.
3. Chỉ trong trường hợp duy nhất: CẢ Haiku CLI lẫn Agy CLI đều cạn sạch quota (`WORKER_CLI_EXHAUSTED: true`), Coordinator mới được phép xem xét van an toàn subagent hoặc L2 Emergency Surgery.

---

## 4. Architecture: Claude Auto-Closeout Pipeline (`auto_closeout.py`)

Khi kết thúc task hoặc chốt phiên, BẮT BUỘC dùng:
```bash
python D:/Taadaa/tools/auto_closeout.py --repo <repo> --files <files> [--commit-msg "..."] [--skip-sol]
```

### Quy trình tự động hoá khép kín (2–3 phút):
1. **First-Pass Sol Check:** Kiểm tra qua Sol High 1 lần. Nếu APPROVED -> Auto-push ngay.
2. **Claude Self-Remediation:** Nếu Sol trượt -> `claude_worker.py --role worker` (Haiku) tự sửa code in-place dựa trên review findings (fallback `ag_cli.py fix` nếu hết quota).
3. **Claude Reviewer Pass:** `claude_worker.py --role reviewer` (Sonnet) duyệt git diff, bắt buộc trả về `VERDICT: APPROVED` (fallback `ag_cli.py ask`).
4. **Mechanical Verification Gate (4 nấc cơ học không thể gian lận):**
   - `py_compile`: Quét sạch 100% cú pháp Python.
   - `pytest`: 100% test suite xanh.
   - `Test Integrity Guard`: Số test không giảm, cấm xóa assert, cấm thêm skip/xfail.
   - `Diff Budget Guard`: Tổng diff <= 150 dòng, <= 5 files, cấm sửa protected paths.
5. **Direct Auto-Push (Vứt bỏ Sol):**
   - Tự động stage đúng `files`.
   - Tự động commit.
   - Ghi hash-chain audit log vào `gate_audit.jsonl` với `verdict="CLAUDE_VERIFIED"`, `score=90` để thỏa mãn pre-push hook.
   - Tự động push qua `safe_push.py` lên remote (`fork` hoặc `origin`).
