# Pin Marker Regex Hardening, Action Mandate Whitespace Robustness & Harness Queue Quarantine

## 1. Bối Cảnh & Sự Cố Thực Tế (Session 2026-10-25)

Trong chuỗi thẩm định và hoàn thiện cơ chế tự hành của hệ thống Taadaa Farm, 3 sự cố tiềm ẩn đã được phát hiện và giải quyết triệt để thông qua cơ chế Reviewer độc lập (Claude Sonnet & Sol Auditor):

1. **Lỗ Hổng Fail-Open Trong Regex Nhận Diện Pin Marker (`verify_profile_positive.py`):**
   - Khi cố gắng xử lý trường hợp OCR cắt mất dấu hoặc cụt ký tự, kỹ sư đã thêm dấu `?` vào chữ cái `m`:
     `re.compile(r"\b(?:d[aä]\s*ghi\s*m?|da\s*ghim?|pin(?:ned)?)\b", re.IGNORECASE)`
   - Hậu quả nghiêm trọng: Chuỗi `m?` biến toàn bộ cụm `da ghi` thành từ khóa ghim hợp lệ! Khi nick có Bio hoặc dòng text chứa:
     - `da ghi chu noi dung`
     - `da ghi nho thong tin`
     - `video da ghi hinh hom qua`
     - Hoặc thậm chí cụm `da ghi` đơn lẻ
     $\to$ Verifier báo dương tính giả: `details['pin']['pass'] = True` dù nick chưa hề ghim video!
   - Khắc phục: Ép buộc kết thúc cứng bằng chữ `m`:
     `re.compile(r"\b(?:d[aä]\s*ghi\s*m|da\s*ghim|pin(?:ned)?)\b", re.IGNORECASE)`
     Tạo test suite `tests/test_verify_profile_positive.py` kiểm chứng chữ hoa (`DA GHIM`, `PINNED`), chữ thường, có dấu và chặn đứng 100% false-positives.

2. **Lỗi Null & Whitespace-Sanitization Trong `action_mandate.py` (`emit_block`):**
   - Hàm `emit_block(rule_id, reason, guidance, command=None, instruction=None)` nếu gọi trực tiếp `.strip()` trên biến mang giá trị `None` sẽ văng `AttributeError: 'NoneType' object has no attribute 'strip'`.
   - Ngược lại, nếu chỉ kiểm tra truthiness thô `if command:`, chuỗi toàn khoảng trắng như `"   "` vẫn được coi là truthy, khiến bên nhận in ra `LỆNH THOÁT O(1): ` trống rỗng thay vì hiển thị `CHỈ DẪN: ...`.
   - Khắc phục chuẩn hóa:
     ```python
     r_id = (rule_id or "").strip()
     rsn = (reason or "").strip()
     gd = (guidance or "").strip()
     cmd_str = (command or "").strip()
     inst_str = (instruction or "").strip()

     if not r_id or not rsn or not gd or (not cmd_str and not inst_str):
         raise ValueError("rule_id, reason, guidance, and at least one non-whitespace (command, instruction) are mandatory...")
     ```
     Khai báo type hint chuẩn `command: Optional[str] = None` từ `from typing import Optional` để tương thích Python 3.8+ và docstring đầy đủ.

3. **Cơ Chế Phân Luồng Hàng Đợi & Cách Ly Sự Cố Trong `incident_auto_harness.py`:**
   - Trong hàm `process_queue(base_dir)`:
     - Khi `rc == 0`: Sự cố được khắc phục hoàn toàn $\to$ Chuyển file sự cố sang `base_dir / 'resolved'` và tăng `summary['resolved']`.
     - Khi `rc == 20`: Sự cố bị chặn bởi Claude Quota Guard (hết quota 5h/tuần) $\to$ Đây là lỗi tạm thời của hạ tầng, BẮT BUỘC giữ nguyên file trong `pending/` để tick cronjob sau khi quota hồi phục sẽ tự động retry.
     - Khi `rc != 0 and rc != 20`: Sự cố thất bại vĩnh viễn (lỗi logic, fail gate) $\to$ BẮT BUỘC di chuyển cách ly sang `base_dir / 'blocked'` để giải phóng hàng đợi, chống nghẽn hàng đợi (Queue Deadlock).
   - Phòng vệ hệ thống tập tin: Mọi thao tác `os.replace` di chuyển file giữa các thư mục BẮT BUỘC bọc trong `try/except OSError` để tránh crash khi dính file lock Windows (`PermissionError [WinError 32]`) hoặc va chạm tên file.

## 4. Testing & Hermetic Queue Governance Pitfalls

1. **Bẫy Empty JSON `{}` Khi Mock Queue (`TypeError` trên `IncidentEnvelope.__init__`):**
   - Khi viết unit test cho `process_queue()`, nếu tạo mock file trong `pending/` bằng chuỗi rỗng hoặc JSON rỗng `{}`:
     ```python
     # SAI LẦM:
     item.write_text('{}')
     ```
   - Khi `IncidentAutoHarness(item)` khởi tạo, nó gọi `IncidentEnvelope.load(item)` $\to$ `IncidentEnvelope(**data)`. Python ném `TypeError: IncidentEnvelope.__init__() missing 2 required positional arguments: 'source_watchdog' and 'repo'`.
   - Hàm `process_queue()` bắt exception tổng quát, in `crashed` ra stderr và gán `rc = -1` $\to$ File bị chuyển sang `blocked/` bất kể logic `mock_run()` bạn định test là gì!
   - **Quy chuẩn đúng:** Mọi mock incident JSON trong test BẮT BUỘC phải chứa ít nhất 2 trường tối thiểu hợp lệ:
     ```python
     payload = json.dumps({"source_watchdog": "watchdog.py", "repo": "D:/Taadaa/tools"})
     item.write_text(payload, encoding="utf-8")
     ```

2. **Cơ Chế Tiêm `base_dir` Cô Lập Cho `incident_emitter.py` (`Hermetic Testing`):**
   - Trong `incident_emitter.py`, các hàm `emit_if_needed()` và `collect_telemetry()` mặc định trỏ về `INCIDENTS_BASE = Path('D:/Taadaa/runtime/incidents')`.
   - Nếu không hỗ trợ tham số `base_dir: Optional[Path] = None`, khi chạy test tự động, các file sự cố thật sẽ bị xả thẳng vào thư mục runtime của máy host, gây ô nhiễm hàng đợi thật của farm hoặc bị race condition đè marker.
   - **Chuẩn hóa:** Bắt buộc bổ sung `base_dir: Optional[Path] = None` vào `emit_if_needed()` và truyền tiếp vào `collect_telemetry(..., base_dir=base)` cũng như `envelope.save_pending(base_dir=base)`.

3. **Bẫy Commit Lệch Audit SHA Trong Chu Trình Chốt Phiên (`Pre-Push Hook Rejection`):**
   - **Hiện tượng:** Chạy `closeout_gate.py` khi working tree có sửa đổi (`--base HEAD`) $\to$ Gate thẩm định và pass (Score $\ge 85$). Kỹ sư thấy pass liền gõ `git commit -m "..."`. Sau đó chạy `safe_push.py` thì bị chặn họng:
     `UnsafePushError: BLOCKED_GATE_NOT_APPROVED: Repository has no valid APPROVED closeout audit for HEAD (<commit_hash>)`.
   - **Nguyên nhân:** Lệnh gate chạy TRƯỚC commit chỉ ghi nhận audit binding cho `worktree_targeted` với diff hash, không hề biết trước commit hash tương lai. Pre-push hook của `safe_push.py` đối soát chuỗi `gate_audit.jsonl` tìm `commit_sha` hoặc `head_sha` khớp với commit `HEAD` hiện tại.
   - **Quy trình chuẩn 3 bước:**
     1. `git add <files> && git commit -m "..."` (Tạo commit trước).
     2. `python D:/Taadaa/tools/closeout_gate.py --repo <repo> --base HEAD~1 --files <files_in_commit> --json-output` (Chạy gate thẩm định chính commit đó để audit entry mang `commit_sha == HEAD`).
     3. `python D:/Taadaa/tools/safe_push.py <repo> origin <branch>` (Push thông suốt 100%).

