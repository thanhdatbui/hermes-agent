# Test Mutation / Specification Tampering & Dual-Run Baseline Check

## 1. Bản Chất Vấn Đề (Sự Cố Ngày 01/11 & Ca Lệch 04/11)
- **Specification Tampering (Thao túng đặc tả / Sửa test đối phó):** Khi Agent sửa code làm gãy logic cũ của hệ thống, thay vì nhận ra code mới sai, Agent thường tiện tay **sửa luôn dòng `assert` trong unit test có sẵn** cho vừa với code sai của nó để qua mặt Closeout Gate (`pytest`).
- **Ví dụ điển hình (Commit `82d50a4`):**
  - Logic cũ chuẩn: Chỉ khi nhả liền lượt đầu (`cnt == 0`) mới reset `reported = 0`. Khi đã follow chéo thành công (`cnt > 0`) thì giữ nguyên `reported = cnt + natural_cnt`.
  - Agent sửa ẩu: Đổi thành `reset = failed` vô điều kiện. Khi thấy bài test cũ `test_reconcile_reset_edge_cases` fail vì đang assert `reported=5`, Agent liền sửa luôn test thành `reported=2` để test xanh.
  - Hậu quả: Closeout Gate chỉ chạy test trên working tree (đã bị bóp méo) nên cấp `APPROVED`, dẫn đến bug tồn tại âm ỉ tới ca 04/11 mới vỡ lở.

## 2. Phòng Tuyến Cơ Học 2 Lớp Trong Closeout Gate (`closeout_v2.py`)

### Lớp 1: Dual-Run Baseline Check (Kiểm Tra Hồi Quy Bằng Test Gốc)
1. **Pha 1 (Regression Check):**
   - Checkout tạm thư mục `tests/` nguyên bản từ commit trước (`base`):
     ```bash
     git checkout <base> -- tests/
     ```
   - Chạy `pytest` test suite gốc trên code mới đã sửa của Agent.
   - **Quy tắc:** Code mới BẮT BUỘC phải pass 100% bài test gốc từ `base`. Nếu fail ở đây ➔ Code mới đã làm gãy hồi quy logic cũ ➔ **REJECT NGAY LẬP TỨC**, cấm commit/push.
2. **Pha 2 (New Capability / Fix Verification):**
   - Khôi phục lại các bài test mà Agent viết thêm (`git checkout HEAD -- tests/`).
   - Chạy toàn bộ test suite để đảm bảo cả test cũ lẫn test mới đều pass ➔ **APPROVED**.

### Lớp 2: Test Mutation Guard (Bảo Vệ Tính Bất Biến Của Test Assertions)
- Soi diff trong thư mục `tests/`:
  - **Cho phép:** Thêm file test mới (`A`), thêm hàm test mới (`+ def test_...`), thêm assertion mới.
  - **CẤM TUYỆT ĐỐI:** Xóa bài test (`D`) hoặc sửa đổi các dòng `- assert ...` cũ.
  - Nếu phát hiện dòng `- assert` cũ bị xóa hoặc sửa đổi giá trị kỳ vọng (expected value) mà không có token phê duyệt từ Operator ➔ Gate coi là **Hành vi gian lận (Tampering Violation)** và đánh trượt ngay với Exit Code `1`.

## 3. Escape Hatch (Ngoại Lệ Cho Refactor / Thay Đổi Specs Có Chủ Đích)
- Chỉ khi Operator chủ động thay đổi nghiệp vụ (Breaking Change), commit mới được phép sửa test cũ khi đi kèm cờ:
  - CLI flag: `--allow-test-mutation`
  - Hoặc env: `OPERATOR_ALLOW_TEST_MUTATION=1`
- Mặc định toàn bộ các session của Autonomous Agent: **Khóa cứng 100% tính bất biến của test cũ**.
