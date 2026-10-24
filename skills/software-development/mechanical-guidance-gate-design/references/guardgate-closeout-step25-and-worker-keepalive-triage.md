# Case Study: GuardGate Step 2.5 Hook & Worker Keepalive Triage (2026-10-24)

## 1. Bối Cảnh Sự Cố & Vòng Lặp Regression
- **Session trước (13/09):** Khắc phục sự cố 16 máy sập USB batch bằng cách nâng `connection_wait_timeout = 20.0s`, `connection_retry_attempts = 3`, `ADB_ONLINE_ATTEMPTS = 5` (Case 162).
- **Session hôm nay (24/10):** Khi thấy máy rớt cáp bị chờ 50 phút, Coordinator táy máy hạ timeout xuống 4.0s để "cho đỡ ngâm", xóa sạch thành quả của Session trước mà pytest chức năng vẫn xanh lè vì chưa có test cơ học cho Case 162.
- **Rà soát hiện trạng:** Thư mục `D:/Taadaa/tools/guardgate` thực chất đã được xây dựng đầy đủ `engine.py`, `rules.json`, `predicates.py`, `runner.py`, nhưng mới chỉ được cắm vào `safe_push.py` mà **chưa được cắm vào `closeout_gate.py`**.

## 2. Giải Pháp Cơ Giới Hóa Step 2.5
Thay vì để diff vi phạm chạy hết test và gọi Reviewer LLM tốn token/thời gian trước khi bị chặn ở `safe_push.py`, hệ thống chèn Step 2.5 vào `closeout_gate.py`:
```python
# Step 2.5: GuardGate Mechanical Invariant Verification (Anti-Regression & Anti-Whining)
try:
    from guardgate.runner import check_diff as _guard_check_diff
    _guard_res = _guard_check_diff(diff_res.diff_text, repo=str(repo_path), auto_quarantine=True)
    if _guard_res.get("status") == "DENY":
        err("[GuardGate DENY] Phat hien vi pham Invariant xuong mau!")
        print(_guard_res.get("mandate", ""))
        write_gate_audit(
            repo=str(repo_path),
            verdict="GUARDGATE_INVARIANT_VIOLATION",
            score=0,
            threshold=85,
            passed=False,
            details=_guard_res,
            audit_binding=audit_binding,
        )
        sys.exit(1)
    ok("GuardGate: All protected invariants satisfied.")
except ImportError:
    pass
```

### Đặc tính Anti-Whining:
- **Tự động dọn dẹp ($O(1)$ Auto-Quarantine):** Tự động `git stash push -m "guardgate-quarantine-..."` đưa file vi phạm về sạch sẽ ngay lập tức.
- **Không có Veto Câm:** Output in rõ `REQUIRED_NEXT_ACTION` với lệnh copy-pasteable cụ thể, cấm viết sớ phân trần/xin lỗi.
- **Strike 3 Guidance Gap:** Sau 3 lần thử vi phạm cùng rule, Gate báo cáo leo thang hướng dẫn, cấm buông xuôi đóng băng phiên.

## 3. Bài Học Về Worker Keepalive Idle Loop (OmniRoute :20129)
- **Triệu chứng:** `dispatch_worker.py` báo `sol_worker.py timed out after 180s`.
- **Nguyên nhân gốc:** Provider `chatgpt-web` trong OmniRoute bị 429 rate limit từ OpenAI. OmniRoute không trả lỗi 429 ngay mà liên tục gửi các chunk SSE keepalive ảo (`chatcmpl-keepalive`) mỗi 2.5s để giữ socket client. `sol_worker.py` nhận keepalive nên không ngắt, ngâm đủ 180s timeout làm tê liệt toàn bộ chuỗi fallback.
- **Khắc phục:** Bắt buộc cài đặt `max_idle_keepalive_timeout` (ngưỡng 45s) cho các client ReAct; nếu quá 45s chỉ nhận keepalive rỗng mà không có content token thì fail-fast sang worker cấp dưới ngay lập tức.

## 4. Bài Học Về Dispatch Max-Turns Truncation
- Tham số `default_turns=6` trong `claude_worker.py` cho role planner quá thấp, khiến Claude Sonnet bị dừng giữa chừng với lỗi `Reached max turns (6)` khi đang khảo sát codebase.
- Role planner/reviewer bắt buộc phải có tối thiểu 15–20 turns để đảm bảo hoàn tất các bản kế hoạch phức tạp.

## 5. Bài Học Về Thắt Cổ Chai Timeout Của Worker Dispatch (`dispatch_worker.py`)
- **Triệu chứng:** Cả Sol Worker (Tier 1) và Agy CLI (Tier 2) đều bị timeout sau 180s dù nội bộ script của chúng được thiết kế cho 300s (`ag_cli.py fix` default 300s, `sol_worker.py` turn timeout 300s).
- **Nguyên nhân gốc:** Thằng Dispatcher bọc ngoài (`dispatch_worker.py`) có default argument `--timeout 180`. Khi dispatch, nó truyền `--timeout 180` đè lên tham số của thợ con, bóp nghẹt các multi-turn web model (cần đọc file -> patch -> test mất 240s-280s) ở phút thứ 3.
- **Khắc phục đồng bộ:** Nâng default `--timeout` của `dispatch_worker.py` và `sol_repair.py` lên 300s.
- **Khóa cơ học chống hạ ngược:** Thêm rule `dispatch_worker_timeout_floor` và predicate `check_dispatch_timeout_floor` vào `guardgate` để cấm bất kỳ session nào táy máy hạ timeout dưới 300s.
- **Quy tắc thiết kế Predicate đa Invariant trong GuardEngine:** Khi nhiều luật cùng áp dụng cho một `tool_class="code_edit", op="commit"`, bắt buộc phải gộp tất cả các invariant predicates vào danh sách `require_all` của master commit rule (ví dụ `["check_case_162_timeout_floor", "check_dispatch_timeout_floor"]`) để tránh việc rule đầu tiên che khuất (shadowing) các rule sau.
