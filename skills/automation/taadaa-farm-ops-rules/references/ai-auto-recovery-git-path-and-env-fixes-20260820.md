# Kỹ Thuật: Khắc Phục Triệt Để 2 Điểm Nghẽn Git Commit & Pytest Của AI Auto-Recovery (20/08/2026)

## 1. Bản Chất 2 Lỗi Khiến AI Auto-Recovery "Commit Thất Bại Hoài"

### A. Lỗi 1: `ImportError: cannot import name '_imaging' from 'PIL'` (Rollback trước 09:20)
- **Nguyên nhân**: AI Auto-Recovery agent (`agent.py`) được spawn từ `automation-core/alerts.py` bằng `sys.executable` (môi trường Hermes Agent venv).
- Khi `code_patcher.py` chạy `pytest`, nó kế thừa biến môi trường `PYTHONPATH` trỏ vào site-packages của Hermes venv (chứa Pillow binary `_imaging.cp311-win_amd64.pyd` không tương thích với Python 3.12).
- Hậu quả: Pytest crash ngay từ bước `collection` trước khi chạy test -> `code_patcher` hiểu nhầm là patch làm hỏng code -> Tự động rollback file và không commit.
- **Cách khắc phục**:
  1. Trong `code_patcher.py`, chuyển lệnh chạy pytest sang dùng cố định binary của farm: `_AUTOMATION_PYTHON = Path(r"D:\Taadaa\python-envs\automation\Scripts\python.exe")`.
  2. Tạo `_AUTOMATION_ENV = dict(os.environ)` và `_AUTOMATION_ENV.pop("PYTHONPATH", None)` để cô lập hoàn toàn môi trường test.

### B. Lỗi 2: `git_failed: [WinError 2] The system cannot find the file specified` (Sau 09:20)
- **Nguyên nhân**: Khi pytest đã pass, code nhảy sang hàm `_git(["commit", ...])` gọi trực tiếp `subprocess.run(["git", ...])`. Tuy nhiên trong tiến trình subprocess chạy ngầm (spawn từ bot/gateway), biến môi trường `PATH` không chứa thư mục cài đặt Git của Windows.
- **Cách khắc phục**:
  - Khóa cứng đường dẫn tuyệt đối chuẩn của Git trong `code_patcher.py`:
    ```python
    _GIT_EXE = str(Path(r"C:\Program Files\Git\cmd\git.EXE"))
    if not Path(_GIT_EXE).exists():
        _GIT_EXE = str(Path(r"C:\Program Files\Git\mingw64\bin\git.EXE"))
    if not Path(_GIT_EXE).exists():
        _GIT_EXE = "git"
    ```

---

## 2. Chuẩn Hóa Các Handler Mới Vào `GEMPHONEFARM_BLIND_POPUP_RULES` (Canonical)
- **Nguyên tắc cốt lõi**: Tránh để AI agent tự ý append các hàm chứa API ảo (`ctx.dump_ui_state()`, `ctx.tap()`) vào cuối `benign_popup.py`.
- Mọi popup in-app trên feed phải được quy hoạch vào danh sách `GEMPHONEFARM_BLIND_POPUP_RULES` trong `feed_swipe_smoke.py`:
  1. **Máy 63 (`comment_input_overlay_back`)**:
     - *Nhận diện*: `//node[@resource-id="...comment_edit_text" or @text="Thêm bình luận..."]`
     - *Hành động*: `action="back"`, `loop=True`.
  2. **Máy 41 (`floating_reward_badge_close`)**:
     - *Nhận diện*: `//node[@text="Nhấp ngay có thưởng" or contains(@text, "có thưởng")]`
     - *Hành động*: `action="tap"`, target `//node[@resource-id="...close_btn" or @text="Đóng"]`.
  3. **Máy 48 (`contact_permission_dialog_deny`)**:
     - *Nhận diện*: `//node[@text="Không cho phép" or @content-desc="Không cho phép"]`
     - *Hành động*: `action="tap"`, target `//node[@text="Không cho phép"]`.
  4. **Máy 35 (`recommendation_or_brand_profile_back`)**:
     - *Nhận diện*: `//node[@text="Mở trang web" or @text="Được đề xuất cho bạn"]`
     - *Hành động*: `action="back"`, `loop=True`.
