# Sol Web (:20129) Coordinator Gate Redesign & Anti-Paralysis Architecture (05/10/2026)

## Bối cảnh & Nguyên nhân gốc rễ (Root Cause Analysis)

Sau quá trình vận hành hệ thống Hard Gate trên toàn bộ các repo Taadaa Phone Farm, Coordinator liên tục rơi vào trạng thái tê liệt (paralyzed/stuck), không thể đưa task về DONE. Phán quyết độc lập của Chief Architect Sol Web (`chatgpt-web/gpt-5.6-sol-high` qua OmniRoute :20129) đã chỉ ra 4 nút thắt chí mạng:

1. **Sol Planning bị biến thành cổng chặn vạn năng cho mọi lệnh Edit:**
   - Trong `guard_dispatch_contract.py`, mọi task `TASK_KIND: EDIT` không thỏa mãn điều kiện T0 (diff < 60 ký tự, thuần hằng số không chứa từ khóa điều khiển) đều bị ép buộc phải có `SOL_PLAN_ID`.
   - Nếu không có plan, hook tự gọi `sol_planner.py` và bất kể thành công hay thất bại đều **CHẶN ĐỨNG DISPATCH** (`[SOL_GATE AUTO-RESOLVE]` hoặc `[SOL_GATE FALLBACK VALVE]`) để bắt Coordinator re-dispatch lại lần 2.
   - Hệ quả: Mỗi lần sửa 1 dòng code bình thường cũng bị chặn ít nhất 1 lần, nhanh chóng chạm trần ngân sách dispatch (`DISPATCH BUDGET EXHAUSTED`) và gây đứt mạch hoàn toàn.
   - **Phán quyết của Sol:** Sửa 1 dòng fix bug thông thường đang bị đối xử ngang với đập đi xây lại cả hệ thống. Hệ thống thiếu bộ phân loại rủi ro (Risk Classifier).

2. **Gate 6 (Visual Evidence Invariant) bị áp dụng cào bằng, phi thực tế:**
   - Quy định *"MAX BLIND STEPS = 1: Mọi thao tác trên Browser/GPM/Farm/UI... BẮT BUỘC chụp ảnh MEDIA:"* bị áp dụng cho mọi ngóc ngách, khiến Coordinator và Worker bị đóng băng khi làm việc thuần code/backend/terminal vì không có UI để chụp ảnh.
   - **Phán quyết của Sol:** Yêu cầu bằng chứng thị giác phải bám theo **Side Effect thực tế** (`UI_MUTATION`), **KHÔNG ĐƯỢC đi theo tool identity hay context**. Tác vụ code-only, test, terminal, đọc log phải được miễn trừ 100% bằng chứng ảnh.

3. **Worker Timeout bị đối xử thành Task Fail (Bẫy Bại Liệt L3 BLOCKED):**
   - Worker subagent gặp timeout mạng hoặc quá giờ (180s/480s) lập tức bị Coordinator coi là thất bại và leo thang lên `L3 BLOCKED`.
   - **Phán quyết của Sol:** Worker Timeout không phải là bằng chứng task thất bại, mà chỉ là tín hiệu mất quan sát tạm thời (`Incomplete Observation`). Bắt buộc phải qua trạng thái `INSPECT_REQUIRED` để kiểm tra diff/artifact thực tế trước khi kết luận.

4. **Terminal của Coordinator bị Default-Deny quá cực đoan:**
   - Trong `farm_policy.py` (`coordinator_terminal_gate`), allowlist chặn cả các lệnh chẩn đoán cơ bản (`echo`, `curl`, `which`, `head`, `tail`, `cat`, `ls`).
   - **Phán quyết của Sol:** Khóa tay đến mức không cho đọc hiện trường khiến Coordinator bị mù, mất hoàn toàn khả năng chẩn đoán O(1).

---

## 4 Trục Kiến Trúc Sửa Đổi Hệ Thống

### 1. Phân tầng Risk Classifier cho Dispatch Gate (`guard_dispatch_contract.py`)
Thay thế cơ chế nhị phân `ALL_EDIT -> SOL_REQUIRED` bằng:
- **HIGH_RISK_CHANGE (Bắt buộc Sol Plan):**
  + Thay đổi kiến trúc core/subsystem boundary, sửa guard/hook/policy.
  + Can thiệp credential, authentication, authorization, secret storage.
  + Thay đổi schema CSDL lớn, migration dữ liệu phá hủy (destructive operations).
  + Sửa trên 3 files hoặc đa repo đồng thời.
- **ROUTINE_CODE_SURGERY (Miễn trừ Sol Plan):**
  + Sửa lỗi nghiệp vụ, cập nhật logic flow, viết test fixture, vá bug tập trung.
  + Chỉ cần Coordinator tự lập **Patch Contract O(1)** chuẩn (`FILE:`, `OLD_STRING:`, `NEW_STRING:`, `FOCUSED_TEST:`) với `anchor c==1` là **cho phép Worker thực thi ngay lập tức, không chặn đòi Sol Plan**.

### 2. Định nghĩa Action Taxonomy cho Gate 6 (Visual Evidence)
- **UI_MUTATION (Bắt buộc MEDIA:):** Thao tác click, tap, swipe, fill form, submit form trên TikTok app, GPM, Browser.
- **CODE_OPERATIONS (Miễn trừ MEDIA: 100%):** Pytest, py_compile, git status/diff, đọc log, inspect ADB read-only, chạy script backend.

### 3. Chuẩn hóa State Machine Timeout Handling
```
RUNNING -> TIMEOUT -> INSPECT_REQUIRED (Live Inspect O(1) <= 30s) -> VERIFY -> DONE / BLOCKED
```
- Khi worker timeout:
  1. Chuyển sang `INSPECT_REQUIRED`.
  2. Coordinator chạy `git status` và `git diff` kiểm tra artifact trên đĩa.
  3. Nếu code đã được ghi và test pass -> nghiệm thu **DONE ngay**.
  4. Chỉ chuyển `BLOCKED` khi có bằng chứng thực tế xác nhận artifact thiếu hoặc lỗi không thể phục hồi.

### 4. Mở rộng Allowlist Terminal cho Coordinator
- Bổ sung vào allowlist các lệnh chẩn đoán an toàn: `echo`, `curl --http1.0 -m 5`, `head`, `tail`, `cat`, `which`, `ls`, truy vấn endpoint local không làm biến đổi trạng thái hệ thống.
