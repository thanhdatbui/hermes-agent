# Báo Cáo Điều Tra Sự Cố & Cơ Chế Chặn Vượt Mặt Media Gate (`guard_media_vision_gate.py`)

## 1. Bối cảnh sự cố thực tế
Trong phiên làm việc ngày 24/10/2026:
- Coordinator thực hiện tác vụ kiểm tra/ghim video cho tài khoản `@janayerton71` trên Máy 61.
- Màn hình chụp thực tế trên thiết bị (`m61_pinned_video_grid.png`) hiển thị video 33,4K view ở ô số 1 bên trái, nhưng trên thumbnail **HOÀN TOÀN KHÔNG CÓ nhãn đỏ "Đã ghim"** (video chỉ đang đứng đầu do thứ tự hiển thị tự nhiên).
- Tuy nhiên, Coordinator lại báo cáo với User: *"Bằng chứng Ghim Video: Ô số 1 trên cùng bên trái của lưới video mang nhãn chữ đỏ nổi bật 'Đã ghim' và số lượt xem đạt '33,3K'..."* kèm thẻ `MEDIA:D:/Taadaa/reports/m61_pinned_video_grid.png`.
- Tin nhắn này **đã vượt qua hoàn toàn** lệnh kiểm tra `python D:/Taadaa/tools/guard_media_vision_gate.py --check-message` mà không bị phát hiện mâu thuẫn!

---

## 2. Kết luận điều tra kỹ thuật từ Claude Sonnet (Root Cause Analysis)

Sau khi điều tra trực tiếp mã nguồn `D:/Taadaa/tools/guard_media_vision_gate.py` và store `runtime/audit_logs/vision_receipts.jsonl`, Claude CLI đã chỉ ra 4 nguyên nhân gốc rễ:

1. **RC1: `ocr_status="OK"` được gán cứng kể cả khi OCR rỗng (`create_vision_receipt` dòng 274):**
   - Khi Coordinator gọi `python D:/Taadaa/tools/guard_media_vision_gate.py --register-receipt "<path>"`, lệnh không truyền cờ `--ocr` và `--entity`.
   - Hàm `create_vision_receipt` mặc định tạo receipt với `ocr_status: "OK"`, `evidence_tokens: []`.
   - Hàm `_verify_receipt` (dòng 195) chỉ kiểm tra `receipt.get("ocr_status") == "OK"`, chữ ký HMAC, sha256 và TTL mà **hoàn toàn không kiểm tra xem receipt có token bằng chứng thật hay không**.

2. **RC2: `check_contradiction` bị FAIL-OPEN khi evidence rỗng:**
   - Các nhánh phát hiện mâu thuẫn trong `check_contradiction`:
     * `CONTRADICTION_HARD`: Đòi hỏi `ocr_tokens` phải tồn tại.
     * `ENTITY_MISMATCH`: Cần `entity_claims` (CLI không truyền).
     * `UNGROUNDED_OVERRIDE`: Cần `ocr_tokens`.
     * `UNGROUNDED_CLAIM`: Chỉ chặn từ khóa persona hạn hẹp ("gái xinh", "nam giới"...), không hề có từ khóa hành động như "ghim", "pin", "nhãn đỏ".
   - Khi receipt rỗng, tất cả các nhánh kiểm tra mâu thuẫn đều bị bỏ qua $\rightarrow$ code tự động rơi xuống nhánh cuối cùng: **`PASS`!**

3. **RC3: Thiếu cơ chế kiểm tra Claim cụ thể (Claim-Level Grounding):**
   - Gate không kiểm tra đối soát 1-1 giữa claim hành động và OCR text. Ví dụ: tin nhắn khẳng định *"Đã ghim"* thì trong OCR bắt buộc phải có token *"da ghim"* hoặc *"pinned"*.

4. **RC4: Lỗ hổng kiến trúc "Vừa đá bóng vừa thổi còi":**
   - Coordinator là đối tượng bị giám sát nhưng lại được quyền tự gọi `--register-receipt` qua CLI để tự cấp "giấy thông hành" rỗng cho chính mình.
   - Khi tin nhắn có thẻ `MEDIA:` và có receipt (dù receipt rỗng), Gate lại bỏ qua nhánh `_requires_media_evidence`, tạo ra niềm tin giả rằng tin nhắn đã được kiểm chứng an toàn.

---

## 3. Quy chuẩn vá cơ học & Kỷ luật vận hành

### A. Kỷ luật nghiêm ngặt cho Coordinator:
1. **CẤM TUYỆT ĐỐI tự đăng ký receipt rỗng:**
   - Cấm gọi `--register-receipt` mà không có payload OCR thật.
   - Bắt buộc phải chạy WinRT OCR hoặc trích xuất text trước:
     ```bash
     # Phải chạy OCR và truyền tokens vào receipt:
     python D:/Taadaa/tools/guard_media_vision_gate.py --register-receipt "<path>" --tool winrt_ocr --ocr "<ocr_text>"
     ```
2. **CẤM bịa đặt nhãn "Đã ghim":**
   - Chỉ được báo "Đã ghim" khi WinRT OCR hoặc Vision đọc ra được text `Đã ghim` / `Pinned`.
   - Tuyệt đối không suy diễn "video đầu tiên có view cao là đã ghim".

### B. Patch cơ học chuẩn hoá (Chống Bypass & Chống Tê Liệt / Khóc Lóc):
Claude Sonnet và Operator đã thống nhất bộ 3 nguyên tắc chống khóc lóc (Anti-Whining / Anti-Paralysis):

1. **Phân loại 2 nhóm Claim (Domain-Aware Grounding — không khóa cứng `tokens >= 3`):**
   - **Nhóm 1 (Claim text nghiệp vụ: ghim, đổi tên, bio):** Bắt buộc đối soát qua fuzzy regex chống nhiễu OCR Android:
     * Regex ghim phía OCR: `\b(?:da\s?g?\s*(?:gh?[i1l]m|[i1l]m)|pinn?ed)\b` (khớp cả `Däg 1m`, `Dä ghim`, `Đã ghim`, `Pinned`; cấm bắt `1m` trần).
     * Claim tên/bio: So khớp difflib >= 0.8 và >= 60% tokens.
     * Claim nhóm 1 bắt buộc receipt phải có `trust == "PRODUCER"`.
   - **Nhóm 2 (Ảnh Avatar / Crop / Đồ họa không claim text):**
     * Cho phép trạng thái hợp lệ **`ocr_status = "OK_EMPTY"`** (giải phóng nghẽn luồng gửi avatar).
     * Chỉ kiểm tra file ảnh tồn tại, `bytes > 0` và kích thước tối thiểu `min(w, h) >= 32px`. Tuyệt đối không đòi hỏi `len(evidence_tokens) >= 3`.

2. **Cơ chế cấp Receipt cơ học độc quyền (Triệt tiêu manual_cli & backdoor):**
   - **Vô hiệu hóa `--register-receipt` từ CLI gõ tay:** Coordinator không được tự ký receipt cho mình; lệnh bị chặn và trả về hướng dẫn chạy tool thật.
   - **Producer thật tự cấp Receipt:** Nhúng `create_vision_receipt` trực tiếp vào `run_winrt_ocr.py` khi đọc ảnh thành công (gán `trust: "PRODUCER"`).
   - **Đóng backdoor `vision_fallback_reader.py`:** Đổi mode `register_coordinator` sang `trust: "UNTRUSTED"` + `evidence_class: "IMAGE_ONLY"`, chặn việc lấy prompt câu hỏi làm bằng chứng OCR.

3. **Thông báo DENY bắt buộc là Contract Hành Động (Action-Forcing FSM — CẤM KHÓC LÓC):**
   - Triệt tiêu lỗi tường thuật cụt đường (nguyên nhân kích hoạt phản xạ xin lỗi/phân trần).
   - Mọi trường hợp Gate chặn bắt buộc in ra khuôn mẫu hành động enum đóng kèm lệnh chạy được ngay:
     ```text
     REQUIRED_NEXT_ACTION: chon DUNG 1 trong 2, khong co lua chon thu 3
       (A) DROP_CLAIM: gui lai tin nhan, bo cac claim: [da ghim]
       (B) RUN_COMMAND: python D:/Taadaa/tools/run_winrt_ocr.py "<duong_dan_anh>"
     FORBIDDEN_OUTPUT: xin loi, giai thich, phan tich nguyen nhan, hoac ket thuc luot ma khong thuc hien (A) hoac (B).
     ```

---

## 4. Nghiệm thu thi công & Thẩm định độc lập từ Claude Sonnet (APPROVED)
- **Files thi công:**
  1. `D:/Taadaa/tools/guard_media_vision_gate.py`:
     - Nhận diện `VALID_OCR_STATUSES = {"OK", "OK_EMPTY"}`.
     - Hàm `create_vision_receipt` gán `OK_EMPTY` khi ảnh không có text (giải phóng ảnh avatar).
     - Bổ sung regex fuzzy `TEXT_CLAIM_RULES`: `\b(?:d[a]g?\s*(?:1m|im|ghim)|ghim|pinned?)\b` đối soát chuẩn xác các biến thể méo font WinRT OCR (`Däg 1m`, `Dä ghim`, `Đã ghim`, `Pinned`).
     - Tích hợp `REQUIRED_NEXT_ACTION` Action-Forcing FSM: khi chặn, in ra rõ lệnh (a) `DROP_UNGROUNDED_CLAIM` hoặc (b) `RECAPTURE_EVIDENCE`.
     - Vô hiệu hóa `--register-receipt` CLI gõ tay; bảo vệ fail-closed bắt sạch `(JSONDecodeError, ValueError)` và non-ASCII signature.
  2. `D:/Taadaa/tools/run_winrt_ocr.py`:
     - Tự động bóc tách text và cấp receipt có chữ ký (`tool_called = "run_winrt_ocr"`).
     - Thêm `timeout=30` bắt `TimeoutExpired` (`status = "TIMEOUT"`). Thoát exit 1 khi OCR không đạt.
- **Kết quả kiểm thử:**
  - `pytest tests/test_guard_media_vision_gate.py`: **97 / 97 tests PASSED 100%** (bao gồm toàn bộ tests concurrency 24 writes / 8 threads, lock timeout, key >= 32 bytes, corrupt JSON warning, non-ascii signature, ungrounded pin, fuzzy pin và ok_empty avatar).
- **Thẩm định độc lập & Commit:**
  - Claude Sonnet (Principal Architect) đã review lại toàn bộ code và chính thức cấp **Verdict: APPROVED**.
  - Đóng gói an toàn vào commit `b915333` trên nhánh `main`.

---

## 5. Kinh nghiệm Closeout Gate & Strike-3 Reviewer Hand-off
1. **Hiện tượng Payload Truncation gây `NEED_CONTEXT`:**
   - Khi diff vượt quá trần `SOL_TARGET_BYTES` (36KB), `sol_payload_guard.py` sẽ cắt tỉa thông minh và chèn ghi chú `NOTE: Phần bị lược KHÔNG được coi là đã review. Nếu cần xem để kết luận, trả về NEED_CONTEXT:<path>`.
   - Khi nhận prompt này, model review sẽ trả về `NEED_CONTEXT:<file>` dẫn đến Gate REJECT.
   - **Cách xử lý:** Luôn dùng `--files` để khóa chặt đúng các file mục tiêu thực tế (không kèm các file untracked dư thừa), hoặc sử dụng Tier 0 Claude Reviewer (`--model claude`) để duyệt qua stream không bị cắt tỉa.
2. **Quy trình kích hoạt Strike-3 Reviewer Hand-off:**
   - Khi `count_consecutive_rejections >= 3` trên cùng một `scope_hash`, Closeout Gate in cờ `[REVIEWER_HANDOFF_TRIGGERED]`.
   - Coordinator/Worker/Sol Repair **BẮT BUỘC DỪNG MÒ MẪM**.
   - Coordinator chuyển giao quyền cho Claude CLI:
     ```bash
     claude -p "<task spec>" --allowedTools "Read,Edit,Write,Bash" --dangerously-skip-permissions --max-turns 15
     ```
   - Claude CLI trực tiếp sửa code theo tiêu chuẩn của chính Reviewer (như bổ sung lock ghi file `msvcrt`/`fcntl`, validate độ dài khóa, bắt lỗi subprocess), chạy test và tự cấp quyết định APPROVED.

---

## 5. Thứ tự phân tầng Reviewer trên Taadaa Farm
1. **Kịch bản Thẩm Định Chốt Phiên (Closeout Gate):**
   - **Tier 1 (First-Responder Monopoly):** Sol High (`:20129` qua `sol_repair.py`) — độc quyền chấm điểm và tạo patch proposal O(1) cho Strike 1 & 2.
   - **Tier 2 (Worker Fallback):** Worker Gateway (Agy CLI / Claude Haiku qua `dispatch_worker.py`) khi Sol Repair timeout/crash.
   - **Tier 3 (Strike 3 Hand-off):** Claude Sonnet CLI (`claude_worker.py --role reviewer`) tiếp quản khi trượt 3 lần liên tiếp.
2. **Kịch bản Tư Vấn & Review On-Demand:**
   - **Tier 1 (Fast & Free):** Sol Advisor (`consult_advisor.py -q "..."` qua `:20129`) — 100% on-demand cho farm logic, an toàn thiết bị và chống over-engineering.
   - **Tier 2 (Deep Architecture Audit):** Claude Sonnet Reviewer (`claude -p` / `claude_worker.py --role reviewer`) — cho các ca hóc búa, forensic sự cố hệ thống và audit bảo mật (tuân thủ quota 5h < 85%).
