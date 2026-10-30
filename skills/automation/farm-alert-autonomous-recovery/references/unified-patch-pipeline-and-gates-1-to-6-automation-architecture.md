# Unified Patch Pipeline & Gates 1-6 Automation Architecture

Tài liệu này ghi lại kiến trúc nối xích cơ học toàn diện từ Gate 1 đến Gate 6 (`unified_patch_pipeline.py`) và quy trình lập Plan O(1) qua Gate B (`gate_b_planner.py`), được hoàn thiện và thẩm định độc lập bởi Claude CLI và Sol High (30/10/2026).

---

## 1. Bản Chất Bài Toán & Lỗ Hổng Lịch Sử
- **Tình trạng cũ (Rời rạc & Nói trước khi làm):**
  - Coordinator LLM thường sinh text khẳng định *"đã dispatch / đang xử lý ngầm"* cùng lượt với tool call, nhưng khi tool bị chặn hoặc fail thì text đã bay ra Telegram $\to$ Gây báo cáo láo / ảo tưởng đang chạy.
  - Sau khi sửa code, Coordinator hay quên bước Canary máy thật hoặc tự ý đóng phiên (Closeout) qua mặt User khi chưa gửi ảnh nghiệm thu.
  - Cũ từng có `plan_exec_gate.py` lên tới 1.700 dòng bị over-engineer (DACL Windows, memory scanning, HMAC rườm rà) khiến tiến trình tự treo >120s dẫn tới Coordinator hoảng loạn nhảy cóc.

---

## 2. Quy Trình Nối Xích 5 Chặng (`unified_patch_pipeline.py`)

Cỗ máy trạng thái (State Machine) thực thi theo chu trình bất khả xâm phạm:

```text
[Lệnh 1 chạm từ User]
       ↓
[S0: PRECHECK (Gate 1 & 5)]
  - Khóa scope --file mục tiêu, kiểm tra path traversal (is_relative_to(repo)).
  - Chặn batch-job (--kind batch -> từ chối ngay).
  - Snapshot baseline git dirty/untracked.
  - Lấy RepoLock OS-level (D:/Taadaa/runtime/locks/) chống 2 pipeline chạy đè lên 1 repo.
       ↓
[S1: PLAN (Gate A & B)]
  - Gọi gate_b_planner.py với thang 3 tầng:
    1. Primary: Gemini Web (Argon 4 Pool qua :20129) - Timeout 120s (đủ sâu để reasoning & failover acc).
    2. Fallback 1: Claude CLI (claude -p) - Timeout 150s.
    3. Fallback 2: Sol Worker (:20129 gpt-web-sol) - Timeout 120s.
    (Timeout tổng chặng: 420s).
  - Xuất plan.json O(1) có exact old_string -> new_string.
  - Kiểm tra điều kiện duy nhất: nl(text).count(old_string) == 1 (chuẩn hóa CRLF->LF, bỏ hoàn toàn SHA256).

### 2.1. CÁC BẪY & KỶ LUẬT THI CÔNG GATE B PLANNER (30/10/2026)
- **Bẫy Context 100 dòng (Anchor Starvation):** `TARGET_CONTEXT_LINES` nếu để 100 dòng sẽ cắt cụt các file >100 dòng (file 500-700 dòng thì phần logic nghiệp vụ bên dưới biến mất hoàn toàn). Planner không thấy code thật sẽ trả về `edits: []`. Bắt buộc đặt tối thiểu 800 dòng hoặc context window động quanh target functions.
- **Bẫy Claude CLI trên Windows (Binary & Argument Resolution):**
  - `shutil.which("claude")` trên Windows có thể trỏ vào wrapper bash không đuôi (`/hermes/bin/claude`), khiến `subprocess.run` văng `WinError 2: The system cannot find the file specified`. Phải ưu tiên `claude.exe` (`shutil.which("claude.exe") or shutil.which("claude")`), nếu là non-exe thì bọc qua `bash`.
  - Claude CLI trên Windows chạy headless dễ treo/lỗi stdin; bắt buộc truyền prompt trực tiếp qua argument `[*base_cmd, "-p", full_prompt]`.
- **Bẫy Gemini Web Schema Drift (Tolerant Parser & Prompt Enforcement):**
  - Gemini Web chat model hay tự ý đổi tên trường (`old_str`/`new_str`, `start_line`/`end_line`, `search`/`replace`) hoặc bỏ quên key `file` khi chỉ sửa 1 file.
  - Bộ validator `validate_plan` bắt buộc hỗ trợ alias mapping và tự gán `single_target` nếu `file` bị khuyết; đồng thời prompt phải có `CRITICAL OUTPUT FORMAT` cấm model tự bịa schema.
       ↓
[S2: PATCH (Gate C)]
  - PRE-SNAPSHOT: Lưu nguyên bản raw bytes mọi file trong scope.
  - Điều phối dispatch_worker.py theo thang: Qoder (Tier 0 DeepSeek-Flash) -> Sol (T1) -> Agy (T2) -> Haiku (T3).
  - HẬU KIỂM ĐỘC LẬP: Tự mô phỏng replace(old, new, 1) trên pre-snapshot và so khớp byte-exact với file thật.
  - GATE 5 GIT-LEVEL: Quét git status sau patch, mọi thay đổi MỚI ngoài scope bị chặn ngay.
  - FULL ROLLBACK: Bất kỳ lỗi nào (worker fail, out-of-scope, syntax hỏng) -> full_rollback() khôi phục cả file trong scope lẫn revert sạch file ngoài scope.
       ↓
[S3: VERIFY (Unit Test)]
  - Chạy focused test < 60s. Test fail -> kích hoạt full_rollback().
       ↓
[S4: CANARY (Gate 6)]
  - Với task farm/device: BẮT BUỘC chạy canary_runner.py trên máy thật (Galaxy S7).
  - Chụp ảnh screencap -> WinRT OCR verify -> Trích xuất thẻ MEDIA:<path>.
  - Thiếu runner hoặc không có ảnh hợp lệ -> FAIL-CLOSED (không được tự skip).
  - Canary fail -> kích hoạt full_rollback().
       ↓
[S5: HOLD & REPORT (Awaiting User)]
  - In khối báo cáo nghiệm thu sạch kèm thẻ MEDIA:<path> gửi Telegram.
  - Ký HMAC-SHA256 vào state.json.
  - Ghi nhận diff_hash_at_hold (gộp cả git diff HEAD và untracked files).
  - THOÁT TIẾN TRÌNH với trạng thái AWAITING_USER.
```

---

## 3. Chốt Chặn Chốt Phiên (`confirm_pipeline`)

Chỉ có một đường duy nhất để đóng phiên:
1. **User gõ xác nhận:** Chỉ nhận đúng các từ khóa chốt phiên chuẩn: `done`, `chốt`, `chốt phiên`, `đóng phiên`.
2. **Xác thực HMAC State:** Đọc và verify chữ ký HMAC của `state.json`. Nếu file bị sửa tay ngoài pipeline $\to$ Từ chối confirm.
3. **Chống Sửa Trộm Code (Anti-Tamper):** So khớp `current_diff_hash == diff_hash_at_hold`. Nếu code bị sửa lén sau lưng User $\to$ Chặn đứng, trừ khi có cờ `--rebaseline` hợp lệ sau remediation.
4. **Kích hoạt Closeout Gate:** Gọi `closeout_gate.py` cho Reviewer chấm điểm $\ge 85/100$ mới được merge/push code. Giới hạn tối đa 3 lần retry (`MAX_CLOSEOUT_RETRIES = 3`).

---

## 4. Chốt Chặn Cơ Học Chống Báo Cáo Láo (`receipt_enforcer.py`)

- Hook trực tiếp vào `gateway/run.py` trước khi bắn tin nhắn ra Telegram.
- Nếu tin nhắn Agent chứa khẳng định *"đã dispatch / đang xử lý ngầm / đã giao worker"* nhưng trong lượt gọi tool không sinh ra `task_id` hợp lệ từ `delegate_task` (hoặc bị Guard chặn whitelist/contract):
- $\to$ Hệ thống cơ học tự động gắn nhãn vạch trần ở cuối tin nhắn:
  `⚠️ [HỆ THỐNG CẢNH BÁO: Chưa có Worker nào chạy thật — Lệnh dispatch vừa bị Guard từ chối do: ...]`.
