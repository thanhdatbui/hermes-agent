# Closeout Gate Diff Ceiling & Dynamic Test Payload Hygiene

## 1. Dynamic Test Payload Sizing vs Hardcoded Ceilings
- **Hiện tượng**: Khi chạy Closeout Gate Step 3 (Focused Tests Execution), một unit test kiểm tra fail-fast trần kích thước diff bị fail bất ngờ:
  `AssertionError: assert True is False where True = DiffResult(success=True, ...).success`
  ở `tests/test_closeout_binding_tamper.py::test_diff_too_large_fail_fast`.
- **Nguyên nhân gốc rễ**:
  - Ban đầu, test case tạo diff giả lập bằng cách ghi 2.000 dòng comment (`~56 KB`) với giả định trần diff `MAX_DIFF_BYTES_GATE = 30_000` (30 KB).
  - Khi hằng số `MAX_DIFF_BYTES_GATE` trong `closeout_gate.py` được nâng lên `120_000` (120 KB) để đáp ứng các đợt refactor nhiều file, payload 56 KB nhỏ hơn 120 KB nên hàm `extract_diff()` trả về `success=True` thay vì `False`.
  - Kết quả: Test fail cứng ở Step 3, làm toàn bộ pipeline Closeout Gate bị dừng trước khi kịp gửi diff cho Reviewer (:20129) chấm điểm.
- **Quy chuẩn sửa đổi (Dynamic Sizing Pattern)**:
  - Tuyệt đối không hardcode số dòng hoặc kích thước byte cố định trong các test case kiểm tra ngưỡng/ceiling.
  - Luôn tính toán kích thước fixture động dựa trên chính hằng số cấu hình của module:
    ```python
    def test_diff_too_large_fail_fast(tmp_path):
        repo = _init_repo(tmp_path)
        # Tính toán động vượt trần MAX_DIFF_BYTES_GATE hiện hành
        line_count = (gate.MAX_DIFF_BYTES_GATE // 20) + 1000
        big_content = "x = 1\n" + ("# comment large diff line\n" * line_count)
        (repo / "hello.py").write_text(big_content, encoding="utf-8")
        subprocess.run(["git", "add", "hello.py"], cwd=repo, check=True)

        diff_res = gate.extract_diff(repo)
        assert diff_res.success is False
        assert "DIFF_TOO_LARGE" in diff_res.error
    ```
  - Pattern này đảm bảo test case luôn luôn đúng kể cả khi production nâng hoặc hạ trần diff `MAX_DIFF_BYTES_GATE`.

## 2. Cơ chế Gom Test Tự Động (Meta-Test Cascade) Trên Repo `tools`
- Khi chạy `closeout_gate.py` với cờ `--files` trên repo `D:/Taadaa/tools`:
  - Ngoài các file test trực tiếp của code mục tiêu (ví dụ `tests/test_tiktok_dashboard.py` khi sửa `tiktok_dashboard.py`), hàm `run_tests()` trong `closeout_gate.py` tự động gom thêm 3 bộ test cốt lõi:
    1. `tests/test_closeout_binding_tamper.py` (chống giả mạo binding audit, TOCTOU attack)
    2. `test_closeout_guard_integration.py` (tích hợp guard)
    3. `test_sol_payload_guard.py` (an toàn payload Sol)
  - Nếu bất kỳ bộ test nào trong 3 bộ cốt lõi này bị lỗi (do môi trường hoặc do hằng số thay đổi), Closeout Gate sẽ fail ngay ở Step 3 (`FOCUSED TESTS FAILED`) với mã thoát 1.
  - Do đó, khi debug Closeout Gate trên repo `tools`, trước khi re-run gate, cần chạy nhanh `pytest` kiểm tra 3 file meta-test này để đảm bảo pass 100%.

## 3. Quy Trình Nghiệm Thu & Đóng Phiên Khi Gặp Lỗi Step 3
1. **Kiểm tra nhật ký lỗi**: Đọc đúng phần `FAILURES` trong stdout của Step 3.
2. **Xác định loại lỗi**:
   - Lỗi do code vừa sửa làm hỏng chức năng cũ $\to$ Vá code nghiệp vụ.
   - Lỗi do test fixture giả lập không khớp với cấu hình hiện tại $\to$ Cập nhật fixture động theo module constant.
3. **Re-run focused test cục bộ**: Đảm bảo lệnh `pytest <test_file> -q` exit 0 trước khi chạy lại `closeout_gate.py`.
