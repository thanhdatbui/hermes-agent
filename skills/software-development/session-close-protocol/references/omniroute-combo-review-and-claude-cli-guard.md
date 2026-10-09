# Review Routing Protocol for Session Closeout (Gate 1)

## Overview & User Policy
Tad đã chuẩn hóa phân tầng định tuyến Review độc lập khi Chốt phiên (Gate 1 Closeout Protocol):
- **Phân tách tuyệt đối giữa Claude CLI Native và OmniRoute (:20129):**
  * **Claude Code CLI (`claude -p --model opus --effort high`):** Là app CLI native của Anthropic cài trên máy host, xác thực trực tiếp qua tài khoản Claude Pro/Team. **Hoàn toàn KHÔNG đi qua OmniRoute**. Chỉ dùng cho ca khó/audit kiến trúc hoặc khi Tad yêu cầu.
  * **OmniRoute (:20129):** Là proxy LLM nội bộ local (`http://localhost:20129/v1`), quản lý pool tài khoản và combo models (Claude Opus/Sonnet, GPT OSS, Nemotron, AG Pool). Dùng cho mọi tác vụ review thường ngày và worker subagent.
- **Review thường / Ca dễ (Mặc định khi Chốt phiên):** BẮT BUỘC gọi combo `review` trên **OmniRoute (:20129)** qua API endpoint (`http://localhost:20129/v1/chat/completions`) hoặc qua `python D:/Taadaa/tools/closeout_gate.py`. Các ca dễ/vận hành (sửa UI selector, tắt switch/toggle, fix lỗi font mojibake, chỉnh config, sửa lỗi cú pháp cục bộ) TUYỆT ĐỐI CẤM gọi Claude CLI native để tránh lãng phí quota 5h của Claude Pro. Nếu model `review` bị timeout quá 90s do tải nặng/concurrency, fallback sang model **`ag-claude`** trên OmniRoute (:20129).
- **Claude Code CLI (`claude -p`):** CHỈ ĐƯỢC PHÉP gọi khi là tác vụ **Review Hard / Ca Khó** (thay đổi sâu trong core/kiến trúc guard, multi-repo sync, state-machine device-lock phức tạp) **HOẶC khi Tad trực tiếp ra lệnh "gọi claude cli"**.
  * **CẤU HÌNH BẮT BUỘC:** Luôn gọi **Claude CLI Opus High** (`claude -p --model opus --effort high`). CẤM TUYỆT ĐỐI tự ý hạ xuống Sonnet. Mọi tham số reasoning đều để cấp độ `high` để bảo toàn quota Claude Pro và giảm latency.
  * **Chốt chặn Hard Guard (85% Limit / Lockout):** Hook `farm-coordinator-guard` chặn đứng vật lý (`action: block`) tại `pre_tool_call` nếu quota 5h chạm trần 85% (38/45 calls) hoặc đang bị Anthropic khóa lockout (ví dụ resets 16:40), tự động ép chuyển hướng sang OmniRoute `:20129`.

## Kỷ Luật Trung Thực Báo Cáo Gate 1 (Review Integrity & Anti-Hallucination)
- **CẤM TUYỆT ĐỐI Coordinator bịa đặt hoặc copy-paste kết quả review cũ:** Không bao giờ mang dòng báo cáo review của phiên trước (ví dụ *"Claude Opus High thẩm định và phê duyệt Hard Capability Lock v2.3"*) dán vào báo cáo của phiên hiện tại (như ca fix 2FA Máy 1).
- **Phản ánh đúng 100% reviewer thực thi:**
  * Nếu phiên chạy qua OmniRoute (:20129): Báo cáo phải ghi rõ: `Gate 1 (Review): OmniRoute (:20129) model review phê duyệt: VERDICT: APPROVED`.
  * Chỉ khi nào terminal thực sự thực thi lệnh `claude -p --model opus --effort high` cho diff của phiên đó thì mới được ghi tên Claude CLI Opus High vào báo cáo.
  * Việc ghi sai/báo cáo ảo reviewer vi phạm trực tiếp nguyên tắc trung thực và tính nhất quán vận hành của hệ thống.

### ⚠️ Bẫy Copy-Paste Template Báo Cáo Chốt Phiên (Hallucinated Reviewer Attribution - 08/09/2026)
- **Hiện tượng thực tế:** Trong phiên chốt ca vận hành 2FA Máy 1 (tắt email 2FA, sticky switcher, fix device_lock và lỗi font UTF-8 — ca dễ), Coordinator khi xuất báo cáo 6 Gate đã sao chép nguyên văn mẫu từ phiên sửa Hermes Guard trước đó:
  `- G1 (Review): Claude Opus High thẩm định và phê duyệt Hard Capability Lock v2.3.`
- **Phản ứng của người dùng:** Người dùng lập tức phát hiện mâu thuẫn và chất vấn:
  * *"Claude opus high này là model từ omni hay sao"*
  * *"R nãy là ca khó hay dễ mà gọi claude cli"*
  Buộc Coordinator phải thú nhận là ca dễ, không hề gọi Claude CLI và bị lẫn text cũ.
- **Quy tắc ngăn chặn:**
  1. **Tạo mới dòng Gate 1 theo runtime thực tế:** Không tái sử dụng block text G1 từ lịch sử chat. Trích xuất đúng model và verdict từ output thật của `closeout_gate.py` hoặc API call của phiên đó.
  2. **Gắn chặt tên tác vụ với diff hiện tại:** Kiểm tra tên feature/bug trong dòng G1 (ví dụ `Case 53 - 2FA Security screen`) phải khớp 100% với diff đang chốt, không được mang tên bản vá của repo/phiên khác (như `Hard Capability Lock v2.3`) sang.
  3. **Quy tắc phân loại nhiệm vụ:**
     - Ca dễ/vận hành (UI toggle, switch, regex, font UTF-8, script report): LUÔN LÀ OmniRoute (:20129) model `review`.
     - Ca khó (kiến trúc guard, race condition device-lock sâu, đa repo phức tạp): MỚI LÀ Claude CLI native (`claude -p --model opus --effort high`).

## OmniRoute Combo `review` Structure
Combo `review` tại `http://localhost:20129/api/combos` được cấu hình với chiến lược `priority` fallover gồm 5 tầng:
1. **Tier 1 (Top Reasoning):** `antigravity/claude-opus-4-6-thinking`
2. **Tier 2 (Primary Code Review):** `antigravity/claude-sonnet-4-6`
3. **Tier 3 (Logic Fallback):** `antigravity/gpt-oss-120b-medium`
4. **Tier 4 (Deep Reasoning Safety Net):** `oc/nemotron-3-ultra-free`
5. **Tier 5 (Final Fallback):** `combo/ag-gemini-pool-3` (18-account pool)

## Calling Recipe for Coordinator (Gate 1)
Coordinator thực hiện gọi HTTP API gọn gàng, fail-fast (socket timeout 45-60s), không dùng shell CLI treo luồng:

```python
import urllib.request
import json
import subprocess

def review_candidate_diff(repo_dir: str, base_ref: str = "origin/master") -> str:
    diff_proc = subprocess.run(
        ["git", "diff", f"{base_ref}..HEAD"],
        cwd=repo_dir,
        capture_output=True,
        text=True,
        encoding="utf-8"
    )
    diff_text = diff_proc.stdout
    if not diff_text.strip():
        # Fallback to unstaged working tree diff if uncommitted
        diff_text = subprocess.run(["git", "diff"], cwd=repo_dir, capture_output=True, text=True, encoding="utf-8").stdout

    payload = {
        "model": "review",
        "messages": [
            {
                "role": "system",
                "content": "You are a senior code reviewer. Review the provided git diff. Focus on farm safety, fail-closed semantics, side effects, and logic errors. Conclude with 'VERDICT: APPROVED' or 'VERDICT: REJECT' with concise bullet points."
            },
            {
                "role": "user",
                "content": f"Please review this diff:\n\n```diff\n{diff_text}\n```"
            }
        ],
        "temperature": 0.1,
        "max_tokens": 1500
    }

    api_key = get_env_var("OMNIROUTE_API_KEY")
    base_url = get_env_var("OMNIROUTE_BASE_URL") or "http://localhost:20129"
    # Chuẩn hóa tránh lỗi lặp /v1/v1 khi base_url đã có /v1 ở đuôi
    if base_url.endswith("/v1"):
        url = f"{base_url.rstrip('/')}/chat/completions"
    else:
        url = f"{base_url.rstrip('/')}/v1/chat/completions"

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        return res["choices"][0]["message"]["content"]
```

## PowerShell Canary Function Isolation (CẤM Dot-Source Trực Tiếp Script PS1 Chứa Top-Level Logic)
Khi kiểm thử canary cho các hàm tiện ích nằm trong script PowerShell chạy batch (như `run_parallel.ps1`, `run_all.ps1`), **CẤM TUYỆT ĐỐI dùng cú pháp dot-source `. 'script.ps1'`** vì PowerShell sẽ thực thi toàn bộ luồng top-level của script (dẫn tới kích hoạt toàn bộ 40-80 máy worker ngoài ý muốn).
- **Kỹ thuật chuẩn an toàn (PowerShell AST Extraction):**
```powershell
powershell -Command "& {
    \$ast = [System.Management.Automation.Language.Parser]::ParseFile('D:\Taadaa\register gmail\run_parallel.ps1', [ref]\$null, [ref]\$null)
    \$fn = \$ast.Find({ \$args[0] -is [System.Management.Automation.Language.FunctionDefinitionAst] -and \$args[0].Name -eq 'Get-RunResultFromLog' }, \$true)
    if (\$fn) {
        Invoke-Expression \$fn.Extent.Text
        \$res = Get-RunResultFromLog -Machine 1 -LogPath 'C:\test_non_existent.log' -ExitCode 1
        Write-Host 'CANARY RESULT:' \$res.Status \$res.Reason
    } else {
        Write-Error 'Function not found'
    }
}"
```

## ⚠️ Pitfall: Agent Memory Drift về Tên Model Review

**Hiện tượng quan sát được (08/09/2026):** Khi user hỏi "Gate 1 dùng model nào?", agent trả lời sai từ memory theo thứ tự:
- Lần 1: "ag-claude = Sonnet" (sai hoàn toàn)
- Lần 2: "ag-opus" (vẫn sai — đây là combo tự nghĩ ra, không tồn tại)
- Lần 3 (sau khi load skill): "combo `review`" (đúng)

**Nguyên nhân:** Agent đọc memory và tự suy luận thay vì load skill để kiểm tra config thực tế.

**Quy tắc bắt buộc:**
- CẤM trả lời "Gate 1 dùng model X" từ memory mà không load skill `session-close-protocol`.
- Khi user hỏi về review routing, LUÔN đọc file này trước khi trả lời.
- Mapping đúng duy nhất: Gate 1 normal = combo **`review`** trên OmniRoute (:20129). Không phải `ag-opus`, không phải `ag-claude`, không phải `ag-gemini-pool-3`.

**Lịch sử log thực tế (cross-session audit 08/09/2026):**
- Phần lớn phiên: combo `review` → VERDICT APPROVED
- Case 141 (07/09 09:01): báo cáo `ag-claude` — khả năng combo `review` timeout, fallback `ag-claude` per quy tắc timeout >90s đã ghi phía trên
- Đây là hành vi đúng (fallback bình thường), không phải config sai

## Bounded Self-Healing Loop
- Nếu reviewer trả về `REJECT`, Coordinator phân tích finding, patch code, chạy test lại, và gửi review lại.
- Tối đa 3 vòng lặp tự sửa trong 1 phiên chốt trước khi dừng lại báo blocker.
- Sau khi nhận được `APPROVED`, tiến hành Gate 2 (Commit) -> Gate 3 (Pull Rebase) -> Gate 4 (Push & Verify).

## Cạm bẫy Empty Diff Khi Đã Có Local Commit Dở Dang (Worker/Subagent Đã Commit Trước)
- **Hiện tượng:** Nếu worker subagent hoặc coordinator đã commit local trước khi gọi Gate 1 (`git commit -m "..."`), việc chạy `git diff HEAD` (hoặc `git diff`) sẽ trả về rỗng (`empty diff`). OmniRoute / 9Router sẽ lập tức trả về:
  `VERDICT: REJECTED (empty diff — no code changes provided for review)`.
- **Giải pháp:** Trước khi trích xuất diff, kiểm tra xem `HEAD` đã khác `origin/<branch>` hay chưa (`git rev-parse HEAD` vs `git rev-parse origin/<branch>`). Nếu local đã có commit, bắt buộc diff so với commit base đầu phiên:
  `git diff origin/master..HEAD` (hoặc `git diff <base_commit> HEAD`) để reviewer audit toàn bộ mã nguồn candidate thực tế.
