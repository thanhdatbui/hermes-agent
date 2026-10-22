# GPM CDP Login-Only: Canary Receipt & canary_matrix.json Setup

## 1. Vấn Đề Canary Receipt Validation Cho Repo GPM
- Khi `done_gate.py` kiểm tra repo GPM auto, nó gọi `canary_runner.check_canary_status()`.
- Hàm này gọi `canary_plan.build_canary_plan()` để load `canary_matrix.json`.
- **Lỗi phổ biến:** Nếu repo name trong `canary_matrix.json` không khớp với tên folder (case-sensitive), hàm trả về `CANARY_PLAN_UNAVAILABLE: "Repo 'GPM auto' chưa có trong matrix"` và gate fail.
- **Fix:** Thêm entry đúng tên vào `D:/Taadaa/tools/canary_matrix.json`:
  ```json
  "GPM auto": {
    "mode": "shadow",
    "exempt_globs": ["**/*.md", "tests/**", "config/**"],
    "fallback": {"hook": "gpm_login_canary", "scope": "single", "coverage": "generic"}
  }
  ```
- **Lưu ý thêm:** `tree_diff_sha256` trong `.canary_passed` phải luôn cập nhật bằng kết quả của `canary_runner.get_working_tree_diff_sha256(repo_dir)`. Hash này thay đổi mỗi khi working tree thay đổi (thêm/xóa/sửa file, kể cả untracked).
- `get_working_tree_diff_sha256()` gọi `git diff HEAD --no-ext-diff` + `git status --porcelain --untracked-files=all` và có thể chạy lâu (>30s) nếu thư mục có nhiều file untracked. Chạy bằng `background=True, notify_on_complete=True`.

## 2. Mẫu Kiểm Thử Cuối Cho GPM CDP Login-Only Mode
Các test case bắt buộc khi refactor `run_oauth_s7_pipeline.py` để đảm bảo pass Sonnet Reviewer:
1. **Lifecycle tests (parametrize):** SUCCESS khi đăng nhập thành công, GDP_START_FAILED khi API lỗi, LOGIN_ONLY_FAILED khi navigation crash, cdp_contexts_empty khi browser trả về contexts rỗng.
2. **cleanup isolation:** Trong `finally:`, nhánh `login_only=True` CHỈ gọi `stop_gpm_profile()`, KHÔNG gọi PowerShell kill; nhánh `login_only=False` KHÔNG gọi `stop_gpm_profile()`, chỉ dọn thư mục cũ.
3. **skip-state tôn trọng:** `antigravity_blacklist`, `cooldown_7days`, `excluded_khoalee` vẫn phải ngăn browser khởi động ngay cả khi `login_only=True`.
4. **avatar negative-cases (parametrize):** aria-label với nhãn "help/terms", aria-label không chứa email, avatar invisible/absent/DOM error, trang landing `/account/about`, body text "Đăng nhập vào tài khoản Google".
5. **telemetry assertion:** `stop_gpm_profile` emit `gpm_stop_failed` khi APIerror hoặc raises exception.
6. **Mock isolation:** Tất cả test bắt buộc mock `gpm_get` trong fixture `_mock_pipeline` để không có gọi mạng thật.

## 3. Pitfall: File `sol_patch.json` Bị Untracked Ảnh Hưởng tree_diff_sha256
- Khi `sol_repair.py` ghi output ra `D:/Taadaa/GPM auto/sol_patch.json`, file này trở thành untracked.
- Hash `tree_diff_sha256` sẽ thay đổi → canary receipt cũ không còn hợp lệ.
- Dọn sạch `sol_patch.json` trước khi tính hash cuối cùng cho receipt.
- Thêm `sol_patch.json` vào `.gitignore` của repo GPM auto để tránh tương lai.
