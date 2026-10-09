# Bẫy Điều Phối Chốt Phiên & Bài Học Siết Rule Canonical (2026-10-05)

## 1. Sự Cố Điều Phối Thực Tế (Root Cause Analysis)
Trong phiên làm việc chốt phiên nuôi acc TikTok, Coordinator đã vi phạm nghiêm trọng kỷ luật điều phối:
1. **Bẫy Clarify Khi Closeout Bị REJECTED (< 85đ):**
   - Khi `closeout_gate.py` trả về điểm 74–83 và phán quyết REJECTED, Coordinator đã dừng lại và gọi công cụ `clarify` để hỏi user có tiếp tục không.
   - Đây là vi phạm trực tiếp `session-close-protocol` và `CANONICAL-POLICY-PRECEDENCE-2026-10-05`: lệnh chốt phiên là mệnh lệnh hành động (`CLOSEOUT_ACTIVE`). Mọi kết quả `< 85` là `REMEDIATION`; Coordinator phải lập Patch Contract, dispatch Worker sửa code/test và chạy lại gate cho đến `APPROVED >= 85`, không dùng `clarify` để xin phép hoặc trốn việc.

2. **Bẫy Tự Sửa Code Monolith T2:**
   - Coordinator đã tự sửa nhiều file production/test (>15 dòng) thay vì dispatch Worker subagent qua `delegate_task`.
   - Hậu quả là dễ ô nhiễm context, lệch EOL CRLF/LF và làm candidate khó truy nguyên.

3. **Bẫy Lẫn Model Routing & Kế Thừa Fallback:**
   - Session chính chuyển sang `omni-worker`/Luna-family do runtime fallback inheritance; không có evidence đủ để kết luận Gemini hết quota.
   - Phải giữ riêng Coordinator, Implementation Worker, Reviewer và Claude CLI. Không dùng output worker làm verdict; không biến Claude CLI thành worker ngầm.

4. **Bẫy Môi Trường Python Sai Khác:**
   - Collection/import lỗi native như PIL `_imaging` phải là fail-closed; không được tiếp tục dùng test pass từ interpreter khác.

## 2. Giải Pháp Siết Rule Canonical
Tư vấn độc lập của Claude Opus chỉ ra cần một nguồn chuẩn duy nhất:

1. **Canonical precedence block:** neo tại `D:/Taadaa/HERMES_SUBAGENT_RULES.md` bằng marker `CANONICAL-POLICY-PRECEDENCE-2026-10-05`; các file `AGENTS.md`, `agent-model-routing`, `session-close-protocol`, `closeout-review-discipline` chỉ trỏ về block và không tái định nghĩa.
2. **Bốn vai trò bất biến:** Coordinator chỉ triage/contract/dispatch/inspect/verify/report; Implementation Worker là executor; Reviewer là read-only gate; Claude CLI chỉ advisory/read-only khi User hoặc active contract yêu cầu.
3. **Closeout state machine:** trigger → `CLOSEOUT_ACTIVE` → `REMEDIATION` khi REJECTED/<85 → Worker patch → focused test → gate lại; chỉ `APPROVED + score>=85 + exit0` mới commit/rebase/push. Transient retry bounded; hard blocker phải có command, exit code và evidence.
4. **Interpreter binding:** trước test/review ghi `sys.executable`, `sys.prefix`, import roots và exact command; collection/native-dependency error vô hiệu hóa evidence cũ.

## 3. Claude CLI Wrapper Pitfall
Khi gọi `C:/Users/Kibe/.codex/skills/claude-final-audit/scripts/invoke-claude-final-audit.ps1`:

- `-Mode Plan` bắt buộc truyền **cả** `-PlanFile` và `-TaskFile`; thiếu `-PlanFile` sẽ fail trước khi Claude tư vấn.
- Trước khi gọi phải chạy quota preflight chính thức; quota result phải được phân biệt với process/wrapper failure.
- Gọi read-only qua wrapper, không tự commit/push. `PARTIAL_NO_VERDICT` hoặc exit nonzero không phải verdict audit; ghi nhận artifact và dùng route review được policy cho phép.

## 4. Evidence Pattern
- Worker self-report chỉ là untrusted handoff; Coordinator phải độc lập đọc diff, chạy focused test và kiểm tra marker/count/hash sau lần write cuối.
- Nếu thư mục không phải Git root, không bịa `git diff`/`numstat`; báo đúng giới hạn binding.
- Khi closeout đang dưới 85, không gọi `clarify`, không báo BLOCKED nếu còn remediation path; đổi contract/worker/chiến lược theo evidence rồi chạy gate lại.
