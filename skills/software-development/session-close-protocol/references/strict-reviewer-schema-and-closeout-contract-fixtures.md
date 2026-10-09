# Strict Reviewer Schema & Closeout State Machine Contract Fixtures

## Use Case
Áp dụng khi kiểm tra, bảo trì hoặc debug **Sol Closeout State Machine** (`closeout_gate.py`) và các test contract (`test_closeout_gate_contract.py`). Đặc biệt khi gặp lỗi:
- `AssertionError: assert 'REVIEW_REMEDIATION_EXHAUSTED' == 'CLOSEOUT_SUCCESS'`
- Test integration `test_main_wires_bounded_remediation_and_second_review` fail với `exit code 1 != 0` sau khi điểm đã đạt 85/90.
- Test ledger chain fail do `verification_boundary` bị gọi ngoài ý muốn trên review điểm 90.

---

## 1. Bản chất của Strict Reviewer Schema (`_validate_approval_schema`)

Trong kiến trúc Closeout Gate của Sol Auditor: **Điểm số đơn thuần ($\ge 85$) KHÔNG ĐỦ để approve**.
Để ngăn chặn agent hoặc reviewer payload "ảo" (hallucinated score / bypass), payload bắt buộc phải thỏa mãn nghiêm ngặt toàn bộ schema:

1. `verdict == "APPROVED"` (case-insensitive string).
2. `score >= SOL_REVIEW_THRESHOLD` (mặc định 85).
3. `evidence` phải tồn tại và KHÔNG rỗng (`review.get("evidence")` truthy).
4. `scorecard` phải tồn tại dưới dạng dictionary (nằm ở top-level `review["scorecard"]` hoặc review tự đóng vai trò scorecard nếu có `score_breakdown`).
5. `ready_to_close is True` (bắt buộc `True` boolean, nằm ở top-level hoặc trong `scorecard`).
6. `score_breakdown` phải là dictionary và chứa đầy đủ **5 trường rubric bắt buộc** (`REQUIRED_RUBRIC_FIELDS`):
   - `logic_correctness` (số: int hoặc float)
   - `test_evidence` (số: int hoặc float)
   - `telemetry_observability` (số: int hoặc float)
   - `farm_safety_regression` (số: int hoặc float)
   - `code_architecture` (số: int hoặc float)
7. Nếu có `overall_score` hoặc `total_score` trong scorecard, giá trị số đó phải $\ge 85$.

Nếu thiếu bất kỳ điều kiện nào, `_validate_approval_schema` sẽ trả về `(False, "<reason>")`, và `_review_verdict` sẽ ép verdict thành `"REJECTED"`.

---

## 2. Các cạm bẫy thường gặp (Pitfalls)

### Pitfall 1: Mock Fixture thiếu rubric / `ready_to_close` dẫn đến REJECT ngầm
- **Hiện tượng**: Viết mock `_review(90)` chỉ trả về `{"verdict": "APPROVED", "score": 90, "evidence": {...}}`.
- **Hậu quả**: `_validate_approval_schema` fail với `"valid scorecard structure required"` hoặc `"ready_to_close must be True"`. State machine coi attempt 2 (hoặc attempt 1) là REJECTED. Sau 2 attempts (max attempts), state machine chuyển sang `REVIEW_REMEDIATION_EXHAUSTED` thay vì `CLOSEOUT_SUCCESS`.
- **Quy tắc**: TUYỆT ĐỐI KHÔNG làm suy yếu logic kiểm tra schema trong production (`closeout_gate.py`). Luôn sửa mock fixture trong test suite để phản ánh đúng payload hợp lệ.

### Pitfall 2: Integration Mock `run_gate_pipeline` để `score_breakdown: {}` rỗng
- **Hiện tượng**: Trong test `test_main_wires_bounded_remediation_and_second_review`, mock `run_gate_pipeline` trả về `scorecard: {"overall_score": 85, "score_breakdown": {}}`.
- **Hậu quả**: Thiếu 5 trường rubric khiến review ở attempt 2 bị reject, `closeout_gate.main()` exit với code 1 thay vì 0.

### Pitfall 3: Ledger test bị trigger verification ngoài ý muốn
- **Hiện tượng**: `test_ledger_chain_integrity_survives_state_machine` mock `_review(90)` với `verification_boundary=lambda: pytest.fail("not needed")`.
- **Hậu quả**: Khi `_review(90)` thiếu schema, attempt 1 bị coi là REJECTED $\to$ chuyển sang `REMEDIATION_REQUIRED` $\to$ gọi `verification_boundary` $\to$ `pytest.fail` nổ.
- Khi fixture đầy đủ schema, attempt 1 thành công ngay lập tức, verification boundary không bao giờ bị gọi.

---

## 3. Chuẩn Fixture mẫu cho Unit & Contract Tests

### Mock helper `_review()` chuẩn:
```python
def _review(score: int, verdict: str | None = None, **extra) -> dict:
    is_approved = (verdict == "APPROVED") if verdict is not None else (score >= 85)
    default_breakdown = {
        "logic_correctness": 30,
        "test_evidence": 25,
        "telemetry_observability": 15,
        "farm_safety_regression": 10,
        "code_architecture": 5,
    }
    scorecard = {
        "overall_score": score,
        "ready_to_close": is_approved,
        "score_breakdown": default_breakdown,
    }
    payload = {
        "verdict": verdict or ("APPROVED" if is_approved else "REJECTED"),
        "score": score,
        "ready_to_close": is_approved,
        "score_breakdown": default_breakdown,
        "scorecard": scorecard,
        "evidence": {"score": score, "source": "mock-review"},
    }
    payload.update(extra)
    return payload
```

### Mock `run_gate_pipeline` cho Integration test:
```python
monkeypatch.setattr(
    closeout_gate,
    "run_gate_pipeline",
    lambda **kwargs: {
        "verdict": ("APPROVED" if (score := next(scores)) >= 85 else "REJECTED"),
        "passed": score >= 85,
        "content": "mock review",
        "scorecard": {
            "overall_score": score,
            "ready_to_close": score >= 85,
            "score_breakdown": {
                "logic_correctness": 30,
                "test_evidence": 25,
                "telemetry_observability": 15,
                "farm_safety_regression": 10,
                "code_architecture": 5,
            },
        },
    },
)
```

---

## 4. Contract Negative Tests bắt buộc
Để đảm bảo contract không bị suy yếu trong tương lai, luôn duy trì các test kiểm tra reject khi payload sai schema:

1. **Score $\ge 85$ nhưng `ready_to_close=False`**: Bắt buộc state machine phải reject, vào remediation hoặc exhausted, ledger ghi nhận blocker `"ready_to_close must be True"`.
2. **Score $\ge 85$ nhưng thiếu trường rubric**: Bắt buộc reject, ledger ghi nhận blocker `"missing required rubric fields"`.
3. **Score $\ge 85$ nhưng trường rubric không phải số**: Bắt buộc reject `"non-numeric values in rubric fields"`.
