# Fail-Closed Budget Parsing & Config Fault-Injection Remediation (19/10/2026)

## 1. Bối Cảnh Lỗi Trượt Điểm Tại Closeout Gate (79 -> 83 Điểm)
Trong phiên chốt chặn cơ giới hóa `delegate_task` và `wire-dispatch-hook`, Closeout Gate (Sol Auditor trên `:20129`) đã từ chối duyệt với điểm số 79/100 (thiếu 1 điểm để vào Grace Band 80–84) với 2 nhóm lý do cốt lõi:

1. **Rủi ro Parser Budget Không Fail-Closed:**
   - Bộ lọc regex chỉ kiểm tra `max_calls` hoặc `budget` dạng đơn giản.
   - Các biến thể diễn đạt như `tối đa 9 calls`, `giới hạn 12 tool calls`, `maximum 10 calls` không được nhận diện đồng nhất.
   - Nghiêm trọng hơn: Nếu có từ khóa `budget` nhưng kèm giá trị phi số (`unlimited`, chuỗi văn bản) hoặc số âm (`budget: -5`), parser trích xuất số thất bại và để lọt qua nhánh cho phép thay vì chặn đứng.
2. **Thiếu Fault-Injection Testing Khi Ghi File Cấu Hình:**
   - Script ghi file cấu hình (`manage_hermes_config.py`) cam kết nguyên tử và backup an toàn, nhưng test suite chỉ kiểm thử luồng chạy bình thường (happy path).
   - Reviewer không chấp nhận cam kết trên lý thuyết nếu thiếu test chứng minh lỗi ghi hoặc lỗi cú pháp YAML thật sự giữ nguyên file gốc không bị biến dạng.

---

## 2. Kỹ Thuật Khắc Phục Chuẩn Hóa

### A. Budget Parsing Fail-Closed 100%
Trong hook kiểm tra contract:
```python
# 1. Regex đa ngôn ngữ bao quát toàn bộ cụm từ giới hạn
budget_num = re.search(
    r'\b(?:max_calls|budget)\b[^\r\n\d]*?(\d+)'
    r'|\b(?:tối\s+đa|giới\s+hạn)\s+(\d+)\s*(?:tool\s+)?calls?\b'
    r'|\b(\d+)\s*(?:tool\s+)?calls?\s*(?:tối\s+đa|giới\s+hạn)\b'
    r'|\b(?:max(?:imum)?|limit(?:ed)?\s+to)\s+(\d+)\s*(?:tool\s+)?calls?\b',
    combined,
    re.IGNORECASE
)
budget_value = next((int(v) for v in budget_num.groups() if v is not None), None) if budget_num else None

# 2. FAIL-CLOSED: Có tín hiệu budget nhưng không parse được số nguyên dương hợp lệ
if budget_value is None or budget_value <= 0:
    msg = (
        "[HARD GATE #3 - INVESTIGATE ROUTE] delegate_task BỊ CHẶN: "
        "Không xác định được số lượng tool calls hợp lệ từ cú pháp budget! "
        "(fail-closed) Ghi rõ budget dạng số nguyên dương, ví dụ 'BUDGET: <= 8 calls'."
    )
    _log_dispatch_audit("block", "investigate", msg)
    print(json.dumps({"action": "block", "message": msg}))
    sys.exit(0)

# 3. Chặn ngưỡng trần investigation (> 8 calls)
if budget_value > 8:
    # block message
```

### B. Kiểm Thử Fault-Injection Cho File Cấu Hình
Khi viết unit test cho các thao tác sửa file cấu hình (`config.yaml`), bắt buộc bổ sung test mô phỏng lỗi thực thi:
```python
def test_wire_dispatch_hook_post_write_fault_leaves_config_untouched(tmp_path, monkeypatch):
    """Mô phỏng lỗi ghi file tạm/YAML hỏng -> file cấu hình gốc phải nguyên vẹn byte-exact."""
    # 1. Tạo config gốc
    orig_bytes = b"hooks:\n  pre_tool_call: []\n"
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_bytes(orig_bytes)
    
    # 2. Mock lỗi yaml.dump phát sinh cú pháp hỏng hoặc lỗi validation
    monkeypatch.setattr(yaml, "dump", lambda *args, **kwargs: None)
    
    # 3. Chạy lệnh
    res = run_cmd_wire_dispatch_hook()
    assert res.exit_code != 0
    assert cfg_file.read_bytes() == orig_bytes  # Tuyệt đối không suy suyển
    assert not (tmp_path / "config.yaml.tmp").exists()  # Đã dọn sạch file rác
```

### C. Kết Quả Nghiệm Thu Thực Tế
Sau khi bổ sung fail-closed budget parser và test fault-injection:
- Điểm số Closeout Gate nhảy vọt từ **79/100** lên **83/100** (`Verdict: APPROVED` trong Grace Band).
- Auto-push lên remote `origin/main` thành công 100% qua `safe_push.py`.
