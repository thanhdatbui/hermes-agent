# Kiến Trúc Chống Regression & Preflight Gate Cho Taadaa Phone Farm

*(Đúc rút từ kiểm tra thống kê 21 ngày log cron farm 24.000 events từ 17/08 đến 06/09/2026, tư vấn thiết kế chuyên sâu và thẩm định APPROVED từ Claude CLI Opus Max)*

---

## 1. BẢN CHẤT LỖI HỒI QUY (REGRESSION: SỬA B LÀM VỠ A) TRÊN FARM

Kiểm tra toàn bộ lịch sử lỗi và git commits cho thấy `cases.md` đã giúp giảm >82% lỗi lặp lại, nhưng các ca regression cục bộ gần đây (điển hình ngày 06/09/2026) đều rơi vào đúng **2 nhóm lỗi bản chất**:

| Ca sự cố thực tế | Lớp lỗi bản chất | Tại sao test cũ không bắt được? | Cơ chế chặn đứng |
|---|---|---|---|
| **Case 124 vs 126:** Thêm kiểm tra placeholder account, thụt lề sai khiến `recaptured_xml` chỉ gán trong `except`, làm các nick bình thường bị crash `UnboundLocalError`. | **Possibly-Unbound** (Biến không chắc chắn được gán ở mọi nhánh rẽ). | Worker chỉ viết test cho nhánh lỗi (placeholder), **không test nhánh chạy bình thường (happy path)**. Linter thường (`ruff`, `pyflakes`) không bắt được vì biến có xuất hiện trong hàm. | **Pyright Gate** (`reportPossiblyUnboundVariable: error`) — tĩnh, < 2 giây, không cần thiết bị. |
| **30/08 (Commit `9eca08a`):** Sửa follow alert suppression nhưng không khởi tạo `loop_start` ở mọi nhánh, làm crash 103 máy và nghẽn 1.507 lock. | **Possibly-Unbound** | Tương tự: chỉ test ca suppression, không test luồng lướt feed chuẩn. | **Pyright Gate** (`reportPossiblyUnboundVariable: error`). |
| **Case 125 vs 127:** Thêm `raw_xml` vào `safety_check()` nhưng quên cập nhật wrapper `safety_check_attempt()`, khiến Máy 46 vẫn bị `focused package unavailable`. | **Signature-Change Omission** (Đổi hàm nhưng caller/wrapper không được sửa cùng). | Worker chỉ gọi trực tiếp hàm con trong unit test, không chạy qua hàm wrapper trung gian. | **`diff_guard.py`** (Quét caller qua `git ls-files "*.py"`) + Module Regression Pack. |
| **Máy 36 (06/09):** Bọc ATX recovery ở Home/Profile navigation nhưng bỏ sót hàm `_sponsored_present()` khi lướt feed. | **Sibling Guard Omission** (Pattern bắt buộc bị bỏ sót ở một số call-site nguy hiểm). | Không rà soát toàn bộ các điểm ném ngoại lệ `ATX_SESSION_UNAVAILABLE`. | **`diff_guard.py`** (`GUARD_RULES`) + Module Regression Pack. |

---

## 2. HỆ THỐNG PHÒNG THỦ 4 LỚP TÍCH HỢP TRONG `tools/preflight.py` (< 15s)

Để giữ trần kỷ luật Worker (< 15 phút, <= 20 tool calls, test < 30s), toàn bộ 4 lớp được gộp vào **1 lệnh duy nhất: `python tools/preflight.py`** (chạy ~6–11s, tốn đúng 1 tool call):

```text
Worker code -> [Lớp 1: Ruff Cú pháp] -> [Lớp 2: Pyright Unbound] -> [Lớp 3: Diff Guard Callers] -> [Lớp 4: Hermetic Module Tests] -> PREFLIGHT: PASS
```

### Lớp 1: Ruff Check (< 1s)
Quét nhanh cú pháp, undefined names (F821), import hỏng trên các file thay đổi trong git diff:
```bash
ruff check --select E9,F821 --quiet <files>
```

### Lớp 2: Pyright Gate — `reportPossiblyUnboundVariable` (< 2.5s)
Tạo file cấu hình `pyrightconfig.gate.json` đặt tại repo root:
```json
{
  "typeCheckingMode": "basic",
  "reportPossiblyUnboundVariable": "error",
  "reportMissingImports": "none",
  "reportUndefinedVariable": "none",
  "reportGeneralTypeIssues": "none",
  "reportOptionalMemberAccess": "none",
  "reportOptionalSubscript": "none",
  "reportPrivateImportUsage": "none",
  "reportAttributeAccessIssue": "none",
  "reportCallIssue": "none",
  "reportArgumentType": "none",
  "reportAssignmentType": "none",
  "reportIndexIssue": "none",
  "reportOperatorIssue": "none",
  "reportRedeclaration": "none",
  "reportReturnType": "none"
}
```
*Lưu ý kỹ thuật đặc biệt (Đã kiểm chứng trên `dist/pyright-internal.js` của Pyright v1.1.413):*
- Tên rule chuẩn xác duy nhất của Pyright trong JS enum và config là `reportPossiblyUnboundVariable` (không phải `reportPossiblyUnbound`).
- Trong chế độ `basic`, tắt toàn bộ các rule type checking legacy để tránh false-positive storm, chỉ giữ lại `reportPossiblyUnboundVariable: error`.
- Bắt ngay lập tức biến dùng ở happy path mà chỉ gán trong `except` hoặc `if/elif`.

### Lớp 3: `tools/diff_guard.py` (< 4-7s)
Script AST nhẹ phân tích git diff so với BASE:
1. **Caller-Omission Check:** Khi hàm thay đổi signature (số lượng tham số, tên tham số), script quét toàn bộ codebase qua `git ls-files "*.py"` (chạy trong 0.07s, cấm dùng `rglob` vì sẽ quét đĩa thư mục `runs/` gây timeout 76s).
   - *Lọc Driver Object:* Bỏ qua attribute call trên các object (`self`, `d`, `device`, `driver`, `cls`, `ctx`) với các method phổ biến (`screenshot`, `reset`, `close`, `run`, `get`, `set`, `update`, `dump`) để triệt tiêu false-positive.
   - *Escape hatch:* Nếu caller thực sự không cần sửa (ví dụ đã dùng kwargs mặc định), thêm comment `# regress-ok: <lý do>`.
2. **Guard-Omission Check:** Kiểm tra các hàm vừa sửa xem có gọi các API nguy cơ (`_capture_xml_text`, `dump_hierarchy`) mà thiếu cơ chế bọc bảo vệ (`atx_recovery`, `ATX_SESSION_UNAVAILABLE`, `reset_atx_agent`). *Lưu ý (Review Finding):* CẤM dùng bare `try|except` trong regex vì bất kỳ khối try/except vô can nào trong hàm cũng làm lọt lỗi. Bắt buộc match đúng cơ chế phục hồi ATX.
3. **Thiết kế Clean API:** Truyền `base: str = "HEAD"` vào hàm `check_diff()`, dời lệnh đọc `sys.argv[1]` vào hàm `main()`, không thực thi side-effect ở module level để test suite import an toàn.

### Lớp 4: Hermetic Module Regression Pack (< 5s)
- **Tự động lọc file tồn tại:** `files = [f for f in raw_files if (ROOT / f).is_file()]` để không bao giờ bị FAIL giả khi commit chỉ xóa hoặc đổi tên file `.py`.
- **Tách bạch Unit vs Device Test:** Chỉ chạy các unit test logic thuần (mock hoàn toàn ADB, chạy trong 1–3s).
- **Self-Test Gác Cổng Pyright ("Test the tester"):** Trong `test_preflight_guard.py`, bắt buộc có test case `test_pyright_gate_flags_possibly_unbound_variable` chạy Pyright trên fixture biến unbound giả lập và assert bắt buộc Pyright phải xuất rule `reportPossiblyUnboundVariable`.
- **Kỷ luật Test Bắt Buộc:** Mọi bản fix B **BẮT BUỘC phải kèm >= 1 test Happy Path** (trường hợp nick chuẩn, dữ liệu chuẩn) để bảo đảm nhánh chính không bị thụt lề sai hay ném ngoại lệ bất ngờ.

---

## 3. IN-CODE ANCHORS TẠI CÁC ĐIỂM NÓNG (INVARIANTS)

Tại các hàm lõi thường xuyên bị sửa (như `verify_and_switch_profile`, `safety_check`, `_sponsored_present`), đặt comment block chuẩn hóa ở đầu hàm:

```python
def verify_and_switch_profile(ctx, target_account, ...):
    # ┌─ REGRESSION-GUARD · module=account_switcher ──────────────────────
    # │ INV-1 [Case126]: Mọi biến dùng sau try/except (như recaptured_xml)
    # │        BẮT BUỘC phải khởi tạo giá trị an toàn (default="") TRƯỚC try.
    # │ INV-2 [Case124]: Khối kiểm tra placeholder candidate phải nằm trong
    # │        nhánh except AccountSwitcherError, không để unindent ra ngoài.
    # └───────────────────────────────────────────────────────────────────
    recaptured_xml = ""  # Khởi tạo mặc định bảo vệ happy path
    ...
```

---

## 4. QUY TRÌNH PHỐI HỢP COORDINATOR ↔ WORKER

1. **Coordinator:** Trước khi dispatch worker, tra cứu nhanh `cases.md` xem hàm sắp sửa có invariant nào, nhồi vào prompt:
   ```text
   === REGRESSION GUARD CONTRACT ===
   - INVARIANTS: Biến dùng sau try/except bắt buộc khởi tạo trước try.
   - TEST: Phải có 1 test happy-path nick bình thường bên cạnh test ca lỗi.
   - GATE BẮT BUỘC: Chạy "python tools/preflight.py" và dán output "PREFLIGHT: PASS".
   ```
2. **Worker:** Sau khi sửa code và viết test, chạy đúng 1 lệnh:
   ```bash
   python tools/preflight.py
   ```
3. **Definition of Done:** Báo cáo kết quả của Worker **bắt buộc phải chứa token máy sinh `PREFLIGHT: PASS`**. Nếu thiếu hoặc preflight báo FAIL, Coordinator từ chối nhận việc và yêu cầu Worker khắc phục ngay.
4. **Hậu kiểm tra độc lập:** Sau khi code hoàn thành và trước khi merge/release diện rộng, gọi Claude CLI Opus Max (`claude -p --model opus --effort max`) kiểm tra để đạt `VERDICT: APPROVED`.
