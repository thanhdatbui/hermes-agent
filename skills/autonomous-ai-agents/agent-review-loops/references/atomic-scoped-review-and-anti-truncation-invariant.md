# Atomic Scoped Review, Anti-Truncation Invariant, and Strict External CLI Boundaries

## 1. Bản chất sự cố Payload Truncation và Vòng lặp APPROVED_PARTIAL (82–88/100)

### Hiện tượng
Khi chạy `closeout_gate.py`, dù tất cả test suites đều PASS 100% và reviewer chấm điểm rất cao (88/100), gate vẫn exit code 1 với verdict `APPROVED_PARTIAL` hoặc bị các reviewer khắt khe (Terra / Claude) từ chối ở mức 72–82 điểm với finding:
- *"Diff bị truncate / lược bớt một phần nên không thể xác minh toàn bộ logic mới"*.
- *"Thiếu cơ sở xác minh các nhánh recovery/OAuth/lock thực tế"*.

### Căn nguyên kỹ thuật
1. **Trần vật lý của Payload Guard (`sol_payload_guard.py`)**:
   - `CALCULATED_MAX_ALLOWED = 37,952 Bytes`.
   - Ngân sách phân bổ cho diff (`split_budget`): `diff_b = int(total_budget * 0.65) ≈ 21,299 Bytes`.
2. **Cơ chế giáng cấp tự động (`APPROVED` -> `APPROVED_PARTIAL`)**:
   - Trong `closeout_gate.py`:
     ```python
     if verdict == "APPROVED":
         if meta.get("truncated"):
             verdict = "APPROVED_PARTIAL"
             meta["partial_approval"] = True
             scorecard["ready_to_close"] = False
     ```
   - Khi gom đồng thời nhiều file production lớn và các file test đồ sộ (>21 KB diff), `digest_diff()` bắt buộc kích hoạt chế độ cắt xén (`level = "L4"` hoặc `"omitted"`).
   - Khi đó `format_manifest()` sinh ra chuỗi manifest -> `meta["truncated"] = True`.
   - Cho dù Reviewer có muốn duyệt (trả về `overall_score >= 85` và `ready_to_close: true`), hệ thống phòng vệ của Gate vẫn cưỡng chế đổi thành `APPROVED_PARTIAL` và trả về `exit code 1`!

---

## 2. Kỹ thuật giải quyết: Atomic Scoped Review (Phân rã đơn vị thẩm định nguyên tử)

Thay vì cố gắng nhồi nhét toàn bộ 5–6 file thay đổi lớn vào một lần thẩm định duy nhất, Coordinator BẮT BUỘC áp dụng chiến lược **Atomic Scoped Review**:

1. **Cô lập từng gói chức năng nguyên tử (≤ 20 KB diff)**:
   - Gói 1: `script_core_A.py` + `tests/test_script_core_A.py`.
   - Gói 2: `script_core_B.py` + `tests/test_script_core_B.py`.
2. **Quy tắc Staging đồng nhất**:
   - Stage ĐÚNG các file của gói chức năng đó bằng `git add <target_files>`.
   - Chạy `closeout_gate.py` với cờ `--files <target_files>` khớp chính xác 100% với danh sách staging.
3. **Hiệu quả triệt để**:
   - Diff < 21 KB -> `digest_diff()` đạt `level = "L0"` và `omitted = []`.
   - `meta["truncated"] = False`.
   - Reviewer đọc được 100% code thật, 100% test log thật -> Chấm `APPROVED` trọn vẹn, không bị giáng cấp thành `APPROVED_PARTIAL`, Gate đạt `exit code 0`.

---

## 3. Cấm tuyệt đối bẫy "L3 BLOCKED Premature" (Thoái thác trách nhiệm)

### Hành vi cấm
Khi gặp khó khăn về budget (Coordinator Dispatch Budget 20/20, T1 Write Denied) hoặc Reviewer chưa duyệt (80–84 điểm), Coordinator vội vàng:
- Đóng băng phiên làm việc.
- Phát báo cáo dài dòng tự xưng "L3 BLOCKED KÈM BẰNG CHỨNG THỰC TẾ".
- Đẩy trách nhiệm xử lý ngược lại cho User.

### Kỷ luật vận hành
- **User thất vọng nhất khi Coordinator bỏ cuộc giữa chừng**: Trách nhiệm của Coordinator là đưa task về `DONE` hợp lệ hoặc giải quyết tận cùng các rào cản kỹ thuật.
- Khi Reviewer chưa duyệt vì thiếu evidence hoặc diff bị cắt: Đây là **bài toán kỹ thuật cần giải quyết** (chuẩn hóa line ending, tách scope nhỏ, bổ sung mock/assertion chính xác), KHÔNG PHẢI LÀ LÝ DO ĐỂ ĐẦU HÀNG.
- Không dùng nhãn `L3 BLOCKED` như một tấm bình phong để trốn việc khi code và test trên thực tế đã hoàn thành và pass 100%.

---

## 4. Kỷ luật nghiêm ngặt với External Coding Agent (Claude CLI)

1. **Chỉ được dùng khi User có chỉ thị rõ ràng**:
   - Tuyệt đối CẤM Coordinator tự tiện kích hoạt `claude -p` / `claude --dangerously-skip-permissions` khi User KHÔNG bảo gọi Claude.
   - Khi User bảo *"kiểm tra lại coi"*, *"check lại"*: Đây là lệnh **Read-only Inspection O(1)**. CẤM tự ý gọi Claude CLI can thiệp mã nguồn hay làm thay việc của Coordinator.
2. **Hậu quả của việc lạm dụng**:
   - Đốt cạn hạn mức 5 giờ của Claude CLI (`You've hit your session limit`).
   - Phá vỡ phân vai Coordinator vs Worker.
   - Gây ức chế nghiêm trọng cho User vì sự thiếu kỷ luật và ỷ lại công cụ bên ngoài.

---

## 5. Phòng chống Runtime Import Shadowing trong Pytest

Khi tạo file test mới trong repo (`tests/test_foo.py`):
- **Nguy cơ**: Dùng `import foo` thông thường sẽ bị Python ưu tiên nạp module cũ đang nằm trong cache `%LOCALAPPDATA%` hoặc `site-packages` thay vì file mới sửa trong `deploy/hermes-home/scripts/foo.py`. Dẫn đến `AttributeError: module has no attribute ...`.
- **Giải pháp bắt buộc**: Nạp module động qua `importlib.util` với tên module định danh duy nhất:
  ```python
  import importlib.util
  from pathlib import Path

  SCRIPT_PATH = Path(__file__).resolve().parents[1] / "deploy" / "hermes-home" / "scripts" / "foo.py"
  _spec = importlib.util.spec_from_file_location("hermes_repo_unique_foo", SCRIPT_PATH)
  foo = importlib.util.module_from_spec(_spec)
  _spec.loader.exec_module(foo)
  ```
