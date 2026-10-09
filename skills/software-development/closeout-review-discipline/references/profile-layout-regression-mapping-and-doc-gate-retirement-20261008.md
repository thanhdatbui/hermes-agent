# Profile Layout Regression Mapping & Obsolete Pre-Commit Doc Gate

## 1. Context & User Directives (08/10/2026)
- **User Clarification:** Hệ thống Phone Farm đã chính thức chuyển đổi từ việc ghi case thủ công trong markdown docs (`docs/farm-automation-cases.md` và `docs/uiautomator.md`) sang **Regression Gate tự động** (bộ unit tests hồi quy trong từng repo + `closeout_gate.py`).
- **Bẫy Pre-Commit Hook Cũ Sót Lại:** Trong repo `Tiktok-video`, `.git/hooks/pre-commit` vẫn gọi `guard_selector_change.py` chứa Rule R2 cũ đòi hỏi phải ghi case vào `docs/farm-automation-cases.md` mới cho commit. Đây là rule cũ lỗi thời đã được thay thế hoàn toàn bởi `closeout_gate.py`.

---

## 2. Bẫy Timeout 120s Do Thiếu Focused Test Mapping Cho Sub-Packages
- **Hiện tượng:** Khi sửa code trong thư mục con của package (ví dụ `scripts/tiktok_workflow/profile_layouts/top_left_pencil.py`), `closeout_gate.py` không tìm thấy test file có tên `test_top_left_pencil.py`.
- **Hậu quả:** Bộ matcher của gate rơi vào nhánh fallback:
  ```python
  cmd = _detect_test_command(repo_path)  # Chạy toàn bộ thư mục tests/ (34 test files)
  ```
  Việc chạy toàn bộ test suite ngốn hơn 120s, kích hoạt hard cap `pytest_timeout = min(timeout_seconds, 120)` $\to$ Gate fail với `Tests timeout sau 120s`.
- **Giải pháp chuẩn hóa trong `closeout_gate.py`:**
  Bổ sung ánh xạ tường minh cho `profile_layout`:
  ```python
  if "state_machine" in stem or "profile_layout" in f_norm:
      for cand in [
          "tests/test_avatar_edit_and_milestone.py",
          "tests/test_profile_golden.py",
          "tests/test_avatar_status_tracking.py",
          "tests/test_lock_inheritance.py",
      ]:
          if (repo_path / cand).exists() and cand not in focused:
              focused.append(cand)
  ```
  Nhờ đó gate chỉ chạy đúng các test liên quan (~17s), tránh timeout toàn cục.

---

## 3. Vượt Ngưỡng Điểm 82 -> 84 -> 86 Của Sol Reviewer (:20129)
Khi Reviewer chấm 82–84/100 cho các thay đổi trong Registry/Layout:
1. **Thiếu Telemetry:** Bổ sung structured metric logging vào code thật:
   - `logger.debug("[PROFILE_LAYOUT] [METRIC] event=top_left_pencil_excluded keyword='%s' bounds=[%d,%d][%d,%d]", ...)`
   - `logger.warning("[PROFILE_LAYOUT] [METRIC] event=overlapping_layouts_resolved chosen=%s matched=%s", ...)`
2. **Chứng Minh Quyền Ưu Tiên Layout (Priority Assertion):**
   - Viết test `test_layout_registry_prioritizes_right_pencil_over_top_left` mô phỏng XML có cả 2 layout và assert `resolve()` ưu tiên `right_pencil`.
3. **Chứng Minh Loại Bỏ Layout An Toàn (Fail-Closed Safety):**
   - Khi loại bỏ `ShareProfileLayout` khỏi REGISTRY, bắt buộc viết test `test_share_profile_layout_excluded_from_registry_fails_closed_safely` chứng minh rằng màn hình chứa icon chia sẻ sẽ fail-closed trả về `UNKNOWN_LAYOUT`, không bị click nhầm mở Share Sheet.
4. **Mở Rộng Test Coverage Bằng Golden Corpus:**
   - Đưa cả `tests/test_profile_golden.py` vào cùng đợt chạy test focused để chứng minh 100% layout cũ không bị hồi quy. Điểm số lập tức tăng lên **86/100 (APPROVED)**.
