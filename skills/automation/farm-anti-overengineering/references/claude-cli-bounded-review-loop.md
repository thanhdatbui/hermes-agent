# Claude CLI Bounded Review-and-Fix Loop (Max 3 Loops to APPROVED)

Pattern được đúc kết khi user yêu cầu: *"Làm đi đến khi nào claude đồng ý thì thôi. Sau đó báo cáo lại. Loop tối đa 3 lần"*.

## 1. Nguyên Tắc Cốt Lõi
- **Reviewer độc lập & Tính xác thực (Authenticity Invariant):** Khi user yêu cầu gọi Claude review ("gọi claude review", "kêu claude kiểm tra", "hỏi claude tư vấn"), Coordinator BẮT BUỘC phải gọi thực tế qua Claude CLI (`claude -p ...`). CẤM TUYỆT ĐỐI Coordinator tự đọc file rồi tự suy diễn, tự đóng vai Claude để nhận xét rồi mạo danh là kết quả của Claude (User phạt: *"Là mày gọi claude review hay mày review v"*).
- **Lựa Chọn Model Review (OmniRoute Combo vs Claude CLI Opus High) — CHUẨN HÓA TOÀN HỆ THỐNG:**
  + **Review / Audit Plan bình thường:** BẮT BUỘC dùng combo OmniRoute review (`:20129`) theo chuỗi đã setup (Opus -> Sonnet -> GPT OSS -> Nemotron -> AG; cấm tự review).
  + **Ca khó HOẶC khi user tự ra lệnh gọi Claude CLI ("gọi claude cli", "kêu claude kiểm tra"):** BẮT BUỘC gọi **Claude CLI native (app CLI, cấm nhầm lẫn với model Claude từ OmniRoute)** với model **Opus ở cấp độ high**:
    ```bash
    claude -p "..." --model opus --effort high
    ```
    CẤM gọi Sonnet. Mọi tham số reasoning/effort đều để cấp độ `high` (vừa đủ sâu, bảo toàn quota Claude Pro và giảm latency).
  + **Xử lý khi Claude CLI chạm Session Limit (`You've hit your session limit`):**
    Khi tài khoản Claude Pro đạt trần hạn ngạch 5h, CLI trả về `You've hit your session limit · resets <time>`. Lúc này Coordinator BẮT BUỘC tự động fallback sang endpoint OmniRoute `:20129` với model `review` hoặc `auto/claude-opus` (`antigravity/claude-opus-4-6-thinking-high`) để tiếp tục quy trình audit độc lập mà không làm gián đoạn phiên làm việc. Báo cáo rõ ràng: *"Claude CLI Pro đạt session limit (reset lúc <time>) -> Tự động chuyển tiếp sang OmniRoute :20129 (`auto/claude-opus`) để thẩm định."*
- **Vòng lặp giới hạn (Bounded Loop):** Tối đa 3 vòng lặp (Round 1 -> Round 2 -> Round 3) đến khi nhận được verdict `APPROVED`.
- **Phân vai nghiêm ngặt:**
  - Coordinator: Trích xuất git diff / spec bài toán, chọn model phù hợp (`opus` cho kiến trúc/hard audit, `sonnet` cho diff thường), gọi Claude CLI review, phân tích verdict (`APPROVED` vs `REJECTED`), bóc tách danh sách blocking findings và dispatch Worker.
  - Worker: Patch code đúng scope theo checklist của Claude, chạy `py_compile` và focused test suite.

## 2. Kỹ Thuật Gọi Claude CLI Qua File Prompt (Chống Lỗi Bash & Vượt Pre-Tool Guard)
Khi gọi `claude -p` trên Windows (Git Bash / MSYS), việc nhúng code diff hoặc prompt dài trực tiếp vào chuỗi lệnh bash thường bị crash:
- Dấu backtick (`` ` ``) bị bash hiểu nhầm là command substitution (`command not found`).
- Dấu nháy kép (`"`) và ký tự Unicode bị escape sai hoặc cắt cụt.
- **Bẫy Pre-Tool Guard:** Nếu bọc bằng `python -c "import subprocess..."`, lệnh `python -c` nhiều dòng ở Coordinator sẽ bị plugin `farm-coordinator-guard` chặn đứng vật lý (`⛔ [FARM GUARD - LONG-RUNNER BLOCKED]`) vì nhầm là python probe/long-runner! Trong khi đó, lệnh `claude -p` lại nằm trực tiếp trong Allowlist Tier 1 của Guard.

**Giải pháp chuẩn hóa toàn diện:**
1. Dùng `write_file` ghi nội dung prompt vào file tạm (ví dụ `C:/Users/Kibe/audit_plan_prompt.txt`).
2. Gọi trực tiếp lệnh `claude -p` đọc nội dung từ file qua cú pháp bash redirection:
```bash
claude -p "$(< /c/Users/Kibe/audit_plan_prompt.txt)" --model opus --effort high
```
*Ưu điểm:* Vừa tránh 100% lỗi escape bash, vừa lọt qua Allowlist của Guard O(1), vừa bảo toàn nguyên vẹn độ dài prompt và ký tự đặc biệt.

Nếu chạy bên trong Worker Subagent (đã có cờ thoát `TAADAA_WORKER=1`), có thể gọi qua script Python `subprocess.run`:

```python
import subprocess

diff_text = """<git_diff_content>"""
prompt = f"""Bạn là Senior Python Code Reviewer.
Hãy review đoạn code diff dưới đây:
{diff_text}

Yêu cầu:
1. Đánh giá Correctness, Safety, Concurrency, Windows OS quirks.
2. Cho VERDICT rõ ràng: APPROVED hay REJECTED kèm lý do cụ thể."""

res = subprocess.run(
    ["claude", "-p", prompt, "--model", "opus", "--effort", "high"],
    capture_output=True,
    text=True,
    timeout=600
)
print(res.stdout or res.stderr)
```

## 3. Quy Trình 3 Vòng Review-and-Fix Thực Tế
| Vòng | Trạng thái Reviewer | Nhiệm vụ của Coordinator & Worker |
| :--- | :--- | :--- |
| **Vòng 1 (Initial Review)** | `NEEDS IMPROVEMENT` | Claude chỉ ra các lỗ hổng kiến trúc (ví dụ: thiếu concurrency lock, Windows `PermissionError`, cú pháp f-string). Coordinator tạo checklist rõ ràng cho Worker. |
| **Vòng 2 (Enforcement Review)** | `REJECTED` | Worker đã vá các lỗi cơ bản nhưng có thể sót logic enforcement (ví dụ: có lock nhưng khi timeout lại không `raise TimeoutError`, thiếu stale lock TTL). Claude phân tích failure path và từ chối duyệt. |
| **Vòng 3 (Verification & Final)** | `APPROVED` | Worker khắc phục dứt điểm điểm thiếu sót cuối cùng. Claude kiểm tra lại toàn bộ logic, xác nhận TOCTOU safety, lock cleanup và cấp verdict `APPROVED`. |

## 4. Tiêu Chuẩn Nghiệm Thu (Post-Approval Verification)
Sau khi nhận được verdict `APPROVED`:
1. Chạy `python -m py_compile <file_da_sua>` đảm bảo 100% không lỗi cú pháp.
2. Chạy focused test suite: `python -m pytest tests/ -k "<module_name>"` xác nhận không có regression.
3. Kiểm tra `git diff` sạch sẽ, giữ nguyên EOL byte-for-byte.

## 5. Xử Lý Từ Khóa "Review" & Quy Chuẩn Báo Cáo (Discipline & Attribution)
- **Nhận diện đúng ý định người dùng:**
  - Khi user nói *"Review lại X..."*, *"Tóm lại review workflow..."*, hay *"Bảo/Kêu claude kiểm tra..."*, trong hệ thống farm điều này KHÔNG có nghĩa là Coordinator tự tổng hợp bằng văn bản của mình.
  - User ĐANG YÊU CẦU: Thẩm định độc lập bằng mô hình bên ngoài qua `claude -p` CLI!
  - Nếu Coordinator tự biên soạn câu trả lời tổng hợp mà không chạy lệnh CLI, user sẽ lập tức bắt lỗi: *"Là mày gọi claude review hay mày review v"*.
- **Quy chuẩn định dạng báo cáo kết quả review & Cấm báo cáo ảo:**
  - BẮT BUỘC mở đầu bằng câu xác thực rõ ràng: *"Đã gọi Claude CLI (`claude -p ... --model <opus|sonnet>`) và nhận được kết quả audit/review sau:"*.
  - Trích xuất trung thực các đề mục chính từ stdout của Claude (Critical, High, Medium, Low, Verdict).
  - Phân tách rạch ròi giữa: (1) Đánh giá gốc của Claude $\leftrightarrow$ (2) Kế hoạch hành động / Code patch mà Coordinator & Worker sẽ thực thi.
  - **CẤM TUYỆT ĐỐI ghi nhận ảo Claude CLI vào báo cáo khi chưa chạy:** Tuyệt đối không copy-paste dòng báo cáo cũ *"Claude Opus High thẩm định và phê duyệt..."* vào các ca dễ (UI toggle, switch, regex, font UTF-8, script report) khi phiên đó chỉ chạy OmniRoute `:20129`. Mọi ca dễ BẮT BUỘC ghi rõ `OmniRoute (:20129) model review phê duyệt: VERDICT: APPROVED`. Ghi sai tên reviewer sẽ bị user chất vấn và vi phạm quy chuẩn trung thực hệ thống (Case 08/09/2026).

