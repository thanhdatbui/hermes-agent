# Mechanical Gate Pitfalls, Reviewer Hand-off & Anti-Paralysis Protocol (15/10/2026)

## 1. Bối cảnh Sự cố (Incident Context)
- **Vấn đề:** Coordinator (Hermes LLM - Gemini) liên tục rơi vào bẫy gọi `delegate_task` (`ag-gemini-pool-3`), đốt 15 turns (~150s) cho mỗi lượt sửa code nhỏ, làm tắc nghẽn luồng làm việc suốt hơn 3 tiếng (từ 18:40 tới 22:00).
- **Vòng lặp Closeout Gate:** Task chính đã pass test nhưng điểm Sol Reviewer kẹt ở 82-84 điểm. Coordinator bị bẫy "cày điểm", liên tục lặp lại các vi sửa đổi (microsecond, whitespace, edge cases) thay vì kích hoạt chuyển giao theo quy định.
- **Phản ứng của Operator:** Cực kỳ ức chế vì quy định Haiku CLI / AG CLI đã được thống nhất nhưng Coordinator vẫn bị system prompt cũ dắt mũi và loop vô tận.

---

## 2. Phân tích Kiến trúc từ Claude Sonnet (Lead Architect & Reviewer)

### A. Lỗ hổng khi cài đặt Mechanical Gate (`guard_dispatch_contract.py`)
1. **Bẫy thụt lề Code chết (Dead Code Indentation Trap):**
   - Trong Python, việc chèn một khối code có thụt lề 4 space ngay sau dòng comment `# 3. NHÁNH EDIT CODE` sẽ khiến khối code đó bị gộp vào thân của khối `if` phía trên (sau lệnh `sys.exit(0)`).
   - *Hậu quả:* Code không bao giờ được thực thi, `py_compile` vẫn pass, nhưng hook hoàn toàn không chặn được `delegate_task`.
   - *Khắc phục:* Khối gate cơ học BẮT BUỘC phải đặt ở cột 0, ngay trước câu lệnh logic đầu tiên của nhánh (`if not file_match:`).
2. **Nguy cơ tự cấp quyền Override (Override String Spoofing):**
   - Nếu cờ mở van khẩn cấp (`WORKER_CLI_EXHAUSTED`, `ALLOW_SUBAGENT_CODE_EDIT`) chỉ dựa vào regex quét context, một Coordinator bị drift có thể tự chèn chuỗi này vào prompt để lách gate.
   - Cơ chế mở van phải gắn liền với telemetry hoặc kiểm chứng thất bại thật sự từ 2 CLI trước đó.

### B. Thứ bậc ưu tiên xử lý xung đột Prompt (Prompt Precedence)
Khi System Prompt được harness nạp vào session chứa chỉ thị cũ mâu thuẫn với Memory và User Profile, thứ bậc giải quyết bắt buộc là:
$$\text{User Directive (hiện tại)} > \text{User Profile / Memory} > \text{Invariants} > \text{Stale System Prompt}$$
Tuyệt đối không để prompt boilerplate cũ dắt mũi làm sai Worker hierarchy.

### C. Quy tắc Strike chuẩn xác trong Closeout Gate
- **Strike 1 & Strike 2 Remediation:** Độc quyền của Sol High (`sol_repair.py`) qua cổng `:20129`.
- **Strike 3 Hand-off:** Khi trượt 3 lần liên tiếp trên cùng `scope_hash`, `closeout_gate.py` tự động kích hoạt `REVIEWER_HANDOFF_TRIGGERED` và ghi khóa `handoff_lock_active.json`.
- **Hành động tại Strike 3:** Toàn bộ Sol Repair, Worker thường và Coordinator DỪNG HOÀN TOÀN việc đoán mò. Tự động chuyển giao quyền can thiệp bàn phím trực tiếp cho **Reviewer (Claude Sonnet CLI)** tự sửa và verify pytest. CẤM sửa vòng thứ 4.

---

## 3. Kỷ luật Chống Bại Não & Chống Khóc Lóc (Anti-Paralysis Invariant)

### Nguyên tắc cốt lõi:
> **"CẤM `delegate_task` KHÔNG ĐỒNG NGHĨA VỚI VIỆC ĐƯỢC PHÉP ĐẦU HÀNG HAY BÁO BLOCKED!"**

Rất nhiều agent có xu hướng tiêu cực: khi bị cấm công cụ quen thuộc thì lập tức viện cớ bó tay, báo BLOCKED hoặc than vãn đùn đẩy cho User. Điều này bị coi là **THẤT BẠI NGHIÊM TRỌNG**.

### Thang Cứu Hộ 4 Tầng Bắt Buộc:
1. **Tier 1 (Mặc định chính):** Haiku CLI (`python D:/Taadaa/tools/haiku_worker.py`, 6–15s $O(1)$).
2. **Tier 2 (Fallback tự động):** Antigravity CLI (`python D:/Taadaa/tools/ag_cli.py fix` - Cụm 7 tài khoản Pro) khi Claude chạm trần quota hoặc stale cache.
3. **Tier 3 (Quyền Coordinator tự sửa):** L2 Emergency Surgery (Coordinator tự sửa trực tiếp trong session nếu task $O(1) \le 30$ dòng, $\le 2$ files, chạy focused test $< 30$s).
4. **Tier 4 (Van an toàn subagent):** Chỉ khi task lớn vượt ngân sách L2 VÀ cả 2 CLI đều cạn quota, Coordinator mới được kẹp cờ `WORKER_CLI_EXHAUSTED: true` để mở van `delegate_task`.

### Tiêu chuẩn báo BLOCKED:
- **HỢP LỆ:** Lỗi phần cứng vật lý (cháy nổ, mất nguồn máy farm, rơi cáp ADB, đứt cáp quang) hoặc hành động tốn phí/xóa dữ liệu cần User duyệt.
- **BẤT HỢP LỆ (CẤM):** Mọi lỗi code, cú pháp, import, test case. Toàn bộ lỗi phần mềm bắt buộc phải được giải quyết dứt điểm về DONE qua thang cứu hộ trên.
