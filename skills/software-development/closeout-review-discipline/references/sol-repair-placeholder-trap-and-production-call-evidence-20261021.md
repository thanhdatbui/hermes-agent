# Sol Repair Placeholder Trap & Production-Function Call Evidence (2026-10-21)

## 1. Context & Root Cause
Trong quá trình chạy Closeout Gate cho các bản vá đăng nhập và quản lý tracking tài khoản (`social_reg_v1.py` và `tiktok_login_v1.py`):
1. **Lần chấm đầu tiên (Score 72/100 REJECT):**
   - Reviewer Sol High trừ nặng điểm `test_evidence` (18/25) vì các bài test chỉ sao chép lại biểu thức production (`center_y = ...; safe_y = ...`) hoặc tự định nghĩa hàm test cục bộ (`verify_re_read`) thay vì gọi trực tiếp hàm production.
   - Judge notes: *"Nhiều test kiểm tra công thức được sao chép hoặc mock luồng thực thi thay vì gọi trực tiếp hàm production, nên có nguy cơ test xanh trong khi mã thật vẫn lỗi."*

2. **Bẫy Proposal của Sol Repair (`pytest.fail` Placeholder Trap):**
   - Khi kích hoạt `sol_repair.py` ở Strike 1 Remediation, mô hình Sol High sinh ra patch cho file test với đoạn mã giữ chỗ:
     ```python
     pytest.fail(
         "Wire this test to the actual tracking-store fixture and inject a row "
         "with conflicting STT, email, TikTok ID, and password. Do not duplicate "
         "the production conflict predicate in the test."
     )
     ```
   - Nếu Coordinator hoặc Worker áp dụng mù quáng proposal này, `pytest` sẽ fail ngay lập tức với `Failed: Wire this test to the actual tracking-store fixture...`.

3. **Bẫy File Handle trong openpyxl Tracking Test (`os.fsync fileno`):**
   - Hàm production `upsert_tracking_account` thực hiện ghi đĩa an toàn bằng `os.fsync(locked_file.fileno())`.
   - Nếu bài test mock `locked_file` bằng `io.BytesIO()`, lệnh gọi sẽ văng `AttributeError: '_io.BytesIO' object has no attribute 'fileno'` và làm rơi vào luồng ghi đè `tracking_pending.csv`.

---

## 2. Invariant & Quy Tắc Thực Thi

### A. Chống áp dụng mù quáng Proposal Sol Repair (Anti-Placeholder-Patch)
- Tuyệt đối CẤM áp dụng trực tiếp proposal của Sol Repair nếu chứa `pytest.fail`, `pytest.skip` vô căn cứ, hoặc các đoạn comment `TODO / Wire this test...`.
- Coordinator/Worker bắt buộc phải đọc nội dung proposal, chuyển đổi các yêu cầu kiểm thử thành code test hoàn chỉnh chạy được 100% trước khi chạy lại Gate.

### B. Chuẩn hóa Fixture File cho Openpyxl Tests
- Khi viết unit test cho các hàm cập nhật workbook có `os.fsync(file.fileno())`:
  ```python
  def test_upsert_tracking_account_production_contract(monkeypatch, tmp_path):
      tracking_file = tmp_path / "tracking.xlsx"
      wb = openpyxl.Workbook()
      ws = wb.active
      assert ws is not None
      ws.append(["May", "Tik", "ID", "PASS", "2FA", "GMAIL", "PASS MAIL", "DOB", "CREATED", "SERIAL"])
      ws.append([24, 7, "user123", "pass123", None, "test@example.com", None, None, None, "serial1"])
      wb.save(tracking_file)
      wb.close()

      class MockLock:
          def __init__(self, f):
              self.file = f
          def __call__(self):
              pass

      monkeypatch.setattr(social, "_backup_tracking_before_write", lambda *a, **k: None)

      # Mở file nhị phân thật để cung cấp fileno() hợp lệ cho os.fsync
      with open(tracking_file, "r+b") as f:
          monkeypatch.setattr(social, "_acquire_tracking_write_phase", lambda reason: MockLock(f))
          row = social.upsert_tracking_account(24, "serial1", "test@example.com", "user123", "pass123")
          assert row == 2
  ```

### C. Triển khai Call Evidence trực tiếp vào Production Function
- Thay vì test công thức toán học rời rạc, hãy gọi trực tiếp hàm production với monkeypatching tối thiểu:
  1. `social.tap_add_account(device_id)`: Monkeypatch `get_ui_xml` và `tap`, assert tọa độ thực tế được truyền vào hàm `tap`.
  2. `social.fill_password_and_login(...)`: Giả lập `wait_for_edittext` timeout (trả về `[]`) để kích hoạt đường fallback duyệt XML.
  3. `social._is_profile_screen_xml(...)` & `social._profile_tab_node(...)`: Truyền trực tiếp các mẫu XML thực tế để kiểm tra ngưỡng lọc tọa độ và bài trừ overlay.
- Kết quả thực tế: Chuyển sang gọi trực tiếp production function đã nâng điểm Sol Reviewer từ 72 lên 78/100 ngay trong lượt kế tiếp.
