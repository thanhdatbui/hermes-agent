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

## 6. Kiến Trúc Multi-Rule Matching Trong GuardEngine (Tránh Rule Shadowing)
- **Vấn đề:** Thiết kế ban đầu của `GuardEngine._match_rule(action)` chỉ lặp qua `self._rules` và trả về rule đầu tiên khớp `(tool_class, op)`. Khi hệ thống có nhiều rule cùng áp dụng cho `(code_edit, commit)` (`case_162_usb_micro_drop_timeout_floor`, `case_161_natural_follow_limit_ceiling`, `dispatch_worker_timeout_floor`), chỉ rule đầu tiên được chạy; các rule sau bị che khuất (shadowed) hoàn toàn, khiến diff vi phạm rule sau vẫn được ALLOW!
- **Giải pháp:** Cải tiến sang `_match_rules(action)` trả về danh sách toàn bộ rules khớp `(tool_class, op)`:
  ```python
  def _decide(self, action: Mapping[str, Any]) -> Decision:
      matching_rules = self._match_rules(action)
      if not matching_rules:
          return Decision(status=DENY, reason="no_matching_rule", next_action="classify_action")

      for rule in matching_rules:
          failed = self._failed_predicate(rule, action)
          if failed is not None:
              on_deny = rule["on_deny"]
              return Decision(
                  status=DENY,
                  rule_id=rule["id"],
                  reason=f"predicate_failed:{failed}",
                  next_action=on_deny["redirect"],
                  strike_class=on_deny.get("strike_class"),
              )
      return Decision(status=ALLOW, rule_id=matching_rules[0]["id"], reason="all_predicates_true")
  ```
  Nhờ đó, mỗi rule giữ trọn vẹn `rule_id`, `on_deny.redirect`, và `guidance` riêng biệt mà không cần gộp chung vào 1 rule khổng lồ.

## 7. Cách Ly File Test Khỏi Predicate Code Edit (Test False-Positive Isolation)
- **Vấn đề:** Khi viết unit test đối kháng (adversarial test) kiểm chứng predicate, test fixture bắt buộc phải chứa diff mẫu vi phạm (ví dụ: `+ parser.add_argument("--timeout", default=180)`). Nếu predicate quét toàn bộ diff mà không nhận diện header file, nó sẽ soi trúng chính đoạn code vi phạm trong file test (`test_*.py`) và ra quyết định DENY ngược lại commit hợp lệ!
- **Giải pháp:** Trong mọi predicate kiểm tra git diff, bắt buộc phải theo dõi header file `+++ b/<path>` và bỏ qua các hunk thuộc file test:
  ```python
  for line in diff.splitlines():
      if line.startswith("+++ b/"):
          curr = line[6:].strip()
          base = os.path.basename(curr)
          is_target_file = (not base.startswith("test_")) and any(curr.endswith(tf) for tf in TARGET_MODULES)
          continue
      if not is_target_file or not line.startswith("+") or line.startswith("+++"):
          continue
      # Soi nội dung vi phạm
  ```

## 8. Chống Lệch Ngưỡng Policy-Implementation (Dynamic Threshold Injection)
- **Vấn đề:** Khai báo `params: {"variable": "timeout", "min_value": 300.0}` trong `rules.json` nhưng trong hàm Python predicate lại hardcode `if val < 300.0: return False`. Khi Operator sửa ngưỡng trong file cấu hình JSON, logic Python không đổi, tạo ra lỗ hổng lệch pha giữa Policy và Thực thi.
- **Giải pháp:** Predicate phải đọc ngưỡng động từ payload rule:
  ```python
  min_val = float(action.get("rule", {}).get("params", {}).get("min_value", 300.0))
  if val < min_val:
      return False
  ```

## 9. Regex Kháng Thứ Tự Tham Số (Order-Insensitive CLI Parsing)
- Khai báo CLI argument trong Python cho phép hoán đổi vị trí thoải mái: `parser.add_argument("--timeout", type=int, default=180)` hoặc `parser.add_argument("--timeout", default=180, type=int)`.
- Regex đơn thuần yêu cầu `--timeout` trước `default` sẽ bị vượt qua dễ dàng khi hoán đổi thứ tự. Bắt buộc kết hợp regex đa mẫu (`p1 | p2`) hoặc tokenization để đảm bảo tính kháng né tránh (adversarial resilience).

