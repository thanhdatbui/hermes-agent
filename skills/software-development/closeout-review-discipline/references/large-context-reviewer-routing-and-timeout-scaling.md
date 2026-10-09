# Large-Context Reviewer Routing, Full-Diff Bypass & Test Timeout Scaling

## 1. Reviewer-Specific Payload Routing: Sol Web vs. Codex Terra / Large-Context Models

### Bối cảnh & Vấn đề
- `sol_payload_guard.py` áp dụng trần cứng 37.952 Bytes (37 KB) để bảo vệ endpoint Sol Web (ChatGPT-web qua OmniRoute `:20129`) tránh lỗi Cloudflare HTTP 413 Payload Too Large.
- Tuy nhiên, khi gửi review tới các model có context window lớn (128k - 200k+) như Codex Terra High (`cx/gpt-5.6-terra-high`), Claude Opus (`ag-opus`), hoặc Codex CLI:
  - Nếu vẫn ép qua `sol_payload_guard`, diff bị cắt xén (L4 truncation) làm mất tới 70-80% code thật.
  - Reviewer Terra/Codex đọc không thấy logic đầy đủ sẽ ngay lập tức trừ điểm nặng ở các tiêu chí: "Diff bị cắt bớt, không đủ cơ sở xác nhận logic", "Unverifiable code branches", "Omitted recovery paths".
  - Thậm chí khi điểm >= 85, `closeout_gate.py` tự động hạ bậc verdict thành `APPROVED_PARTIAL` vì cờ `meta['truncated'] == True`.

### Quy tắc định tuyến Payload (Invariant)
1. **Sol Web (`chatgpt-web/*`, model `review` mặc định trỏ Sol)**: BẮT BUỘC dùng `sol_payload_guard` để bảo vệ HTTP payload không vượt 37 KB.
2. **Codex Terra & Large-Context Models (`cx/*`, `terra`, `codex`, `claude`, `opus`)**: BẮT BUỘC bỏ qua trần `sol_payload_guard` (`bypass_payload_guard=True`). Ném trọn vẹn 100% diff và verified test evidence lên để reviewer đọc toàn bộ mã nguồn thực tế.
3. **Cơ chế Auto-Fallback Sol Web → Terra Codex (`cx/gpt-5.6-terra-high`)**:
   - Khi gọi review mặc định (`model="review"`) và diff vượt trần (~24KB) dẫn đến `truncated=True`, hệ thống tự động bốc toàn bộ un-truncated diff chuyển sang `cx/gpt-5.6-terra-high` để thẩm định không bị mất ngữ cảnh.
   - **Fail-Closed Constraints Bắt Buộc**:
     - *NEED_CONTEXT Precedence*: `NEED_CONTEXT:` phải được kiểm tra trước verdict `APPROVED`; nếu reviewer yêu cầu context, lập tức trả về `NEED_CONTEXT` fail-closed (không để rubric score đè).
     - *Provider-owned size & Trần an toàn 4 MiB*: Bypass chỉ là bypass **Sol Web's** payload guard. Không đặt cap nhân tạo nhỏ (như 512 KiB) gây nghẽn diff vì Terra được chọn để đọc payload lớn ("gửi nặng thoải mái"). Để vừa chấp nhận diff lớn vừa chống tràn bộ nhớ/DoS, áp dụng trần an toàn hào phóng 4 MiB (4,194,304 bytes).
     - *Exact Fallback Model Allowlist*: Chỉ kích hoạt fallback sang đúng model `cx/gpt-5.6-terra-high`; không dùng heuristic marker để mở bypass cho model khác.
     - *Fallback Error Handling*: Khi Terra gặp lỗi (timeout/5xx/malformed JSON), bắt buộc bắt exception, ghi nhận `meta['fallback_error']` và byte count/source-target model; không được biến response thiếu bằng chứng thành APPROVED.
     - *Binding Integrity & Canonical Hash*:
       - `extract_diff(targets=...)` và `resolve_audit_binding(targets=...)` phải dùng chung một helper canonical diff bytes đồng nhất (`--binary`, `--no-color`, `--no-ext-diff`, `--no-textconv`, `-c core.quotepath=off`).
       - Pre-review SHA comparison: dừng pipeline ngay trước khi gọi reviewer nếu extracted diff SHA lệch binding SHA.
       - Post-review SHA comparison: thiếu review SHA hoặc review SHA khác binding SHA bắt buộc fail-closed (`verdict="BINDING_MISMATCH"`, `passed=False`).
     - *Bẫy MIN_DIFF_CHARS = 50 khi viết fixture test*: Pipeline có kiểm tra độ dài tối thiểu của diff (`< 50 chars` sẽ văng lỗi `Diff too short`). Các test mock pipeline (như test hash mismatch) bắt buộc phải dùng chuỗi diff dài $\ge 50$ ký tự để không bị chết sớm ở bước trích xuất diff.
     - *Test Evidence Matrix*: Suite test bắt buộc phủ đủ: (a) route Terra full-diff không bị cap, (b) Terra/provider fallback lỗi, (c) NEED_CONTEXT precedence, (d) binding SHA match/mismatch, (e) telemetry audit `review_matches_binding`, và (f) scoped staged/worktree/untracked boundaries.

---

## 2. Test Timeout Scaling & Cache Provider Hygiene

### Bối cảnh
- Khi một phiên thay đổi chạm vào nhiều module sản xuất (+50 test cases), thời gian chạy pytest có thể tăng từ 20s lên 120s - 130s.
- Nếu `closeout_gate.py` hard-cap timeout pytest ở mức 120s:
  - Pipeline bị fail tại Step 3 với lỗi `Tests timeout sau 120s (0 failed, 1 errors)`.
  - Đây là lỗi execution hạ tầng, không phải code bug, nhưng làm fail toàn bộ gate.

### Quy tắc kiểm thử Focused Gate
1. **Timeout**: Nâng timeout chạy pytest lên `min(240, remaining_for_test)` khi test suite mở rộng.
2. **Cache Provider**: Luôn chạy pytest với cờ `-p no:cacheprovider` để tránh cache lock, stale bytecode hoặc directory access permission issues trên Windows.
3. **Module Shadowing**: Bắt buộc import file repo bằng `importlib.util.spec_from_file_location` với tên module độc nhất để tránh đụng độ với module runtime trong `%LOCALAPPDATA%/hermes/scripts/`.

---

## 3. Kỷ luật điều phối: Chống buông xuôi và cấm viện cớ L3 BLOCKED

1. **User cực ghét thái độ viện cớ an toàn / rule để đóng băng**:
   - Khi gate chưa pass (điểm 75 - 84), tuyệt đối không được viện cớ "hết budget", "rule an toàn", "chuyển L3 BLOCKED" để phủi tay đẩy việc lại cho User.
   - Bắt buộc phải đào sâu log phán quyết của Reviewer: tìm chính xác nguyên nhân (lỗi import? truncation? thiếu test nhánh nào? lỗi startup log()?).
   - Trực tiếp sửa triệt để các finding kỹ thuật cụ thể cho tới khi Reviewer chấm APPROVED >= 85.
2. **Tuyệt đối không tự ý gọi Claude CLI**:
   - Chỉ được gọi Claude CLI khi User đích danh yêu cầu. Cấm tự ý gọi ngầm đốt quota của User.
