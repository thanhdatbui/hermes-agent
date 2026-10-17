# Call-Site Safety Helper Enforcement & Negative Test Evidence (Closeout Review Lessons 2026-10-17)

## 1. Hiện Tượng Reviewer Sol Auditor Trừ Điểm Kép (74 -> 79/100)
Trong các bản vá tăng cường tính ổn định cho quy trình tự động hóa (ví dụ: chờ biến mất loading spinner `tux_loading_hud`, hoặc kiểm tra trạng thái offline mạng):
- **Sai lầm 1: Tạo Helper Kiểm Tra Nhưng Call Site Không Thực Thi Kết Quả (No Call-Site Gate)**:
  * Helper `_wait_for_profile_loading_spinner` trả về `bool` (`True` nếu spinner biến mất, `False` nếu timeout hoặc dump UI lỗi).
  * Nhưng tại call site trong `verify_and_switch_profile`, hàm chỉ gọi:
    ```python
    _wait_for_profile_loading_spinner(ctx, step=...)
    latest_identity = _read_profile_identity(...)
    ```
  * Call site hoàn toàn bỏ qua giá trị trả về! Dù spinner có bị timeout hoặc giao diện đang kẹt lỗi dump, code vẫn tiếp tục gọi `_read_profile_identity` như bình thường.
  * **Đánh giá của Reviewer**: *"Điểm trừ lớn nhất là kết quả timeout hoặc dump_error của cơ chế chờ spinner không chặn việc đọc profile identity, khiến điều kiện an toàn được thiết kế nhưng không được thực thi tại call site."* (Điểm trừ nặng tại Logic Correctness & Farm Safety).

- **Sai lầm 2: Thiếu Negative Test Evidence (Kiểm Thử Nhánh Bỏ Qua)**:
  * Unit test chỉ kiểm tra helper hoạt động độc lập (`_wait_for_profile_loading_spinner` trả về True/False).
  * Không có bất kỳ test case nào ở tầng flow tích hợp chứng minh rằng: **Khi helper trả về False, các hành động nhạy cảm phía sau (như `_read_profile_identity`) BỊ CHẶN LẠI và KHÔNG ĐƯỢC PHÉP CHẠY**.

## 2. Quy Chuẩn Khắc Phục Dứt Điểm (The Enforcement Pattern)

### A. Call-Site Bắt Buộc Fail-Closed
Khi một helper an toàn trả về `bool`, call site bắt buộc phải bọc điều kiện rẽ nhánh và ngắt nhịp:
```python
if not _wait_for_profile_loading_spinner(
    ctx,
    step=f"{SESSION_ARTIFACT_PREFIX}/profile_preflight_verify_{attempt}",
):
    last_reason = "profile loading spinner still visible or UI dump failed"
    continue  # hoặc fail-fast ném lỗi / thoát an toàn
```

### B. Negative Test Evidence Bắt Buộc Phải Có
Trong test suite (ví dụ `test_feed_swipe_smoke.py`), bắt buộc bổ sung test case mô phỏng tình huống timeout/lỗi và khẳng định bằng chứng phủ định:
```python
def test_verify_and_switch_profile_skips_identity_read_when_spinner_times_out(self) -> None:
    # Mock spinner wait trả về False
    with patch("flows.feed_swipe_smoke._wait_for_profile_loading_spinner", return_value=False) as spinner_mock, \
         patch("flows.feed_swipe_smoke._read_profile_identity_with_add_phone_guard") as read_identity_mock:
        row = verify_and_switch_profile(ctx, "expected_user")

    # Xác nhận: Status báo lỗi an toàn, spinner được gọi, và bước đọc identity phía sau KHÔNG ĐƯỢC PHÉP CHẠY
    self.assertEqual(row["status"], ExitStatus.MANUAL_NEEDED.value)
    self.assertIn("loading spinner", row["reason"])
    self.assertEqual(spinner_mock.call_count, 3)
    # read_identity_mock chỉ được gọi ở preflight ban đầu (1 lần), các lần post-switch sau spinner timeout đều bị skip
    self.assertEqual(read_identity_mock.call_count, 1)
```

## 3. Checklist Trước Khi Submit Closeout Gate
1. **Helper có trả về boolean/result không?** $\rightarrow$ Call site đã kiểm tra `if not result:` chưa?
2. **Khi helper fail, luồng đi đâu?** $\rightarrow$ Có gán lý do lỗi `last_reason` và `continue`/`break`/`return` chưa?
3. **Có test case cho cả 2 nhánh chưa?**
   - Nhánh Happy Path (spinner cleared $\rightarrow$ proceeds).
   - Nhánh Unhappy Path (spinner timeout / dump error $\rightarrow$ skips downstream actions).
4. **Targeted commit hygiene**:
   - Dùng `git commit --amend` để gộp code fix và test case vào cùng một commit duy nhất.
   - Chạy `closeout_gate.py --base HEAD~1 --files <code_file> <test_file>` để cô lập scope đánh giá của Reviewer.
