# Profile Layout Selector Guard Rule R2 & Golden Manifest Contract

## 1. Hiện tượng & Triệu chứng chặn Commit
Khi chỉnh sửa bất kỳ tệp tin nào thuộc thư mục `scripts/tiktok_workflow/profile_layouts/` trong repo `D:/Taadaa/Tiktok-video`:
Lệnh `git commit` ngay lập tức bị pre-commit hook (`tools/guard_selector_change.py`) chặn đứng với thông báo lỗi:
```text
SELECTOR_GUARD REJECT: R2: Sửa profile_layouts bắt buộc kèm cập nhật docs/farm-automation-cases.md.
SELECTOR_GUARD REJECT: R2: Sửa profile_layouts bắt buộc kèm golden dump.xml thu thập từ máy thật trong tests/golden/profile/.
❌ COMMIT BLOCKED: Vi pham selector hoac anti-skip guard!
```

---

## 2. Nguyên tắc & Kiến trúc Selector Guard (`guard_selector_change.py`)
Hệ thống sử dụng bộ lọc bảo vệ nghiêm ngặt chống thoái hóa selector:
- **R0 (Anti-Tamper):** Cấm tuyệt đối sửa đổi các công cụ giám sát (`tools/guard_selector_change.py`, `closeout_gate.py`, `tests/test_profile_golden.py`).
- **R1 (Monolith Protection):** Cấm sửa trực tiếp vùng `PROFILE_SELECTOR_DELEGATE` trong `state_machine.py`. Mọi logic selector phải nằm trong `profile_layouts/`.
- **R2 (Protocol Discipline):** Bất kỳ thay đổi nào trong `profile_layouts/` bắt buộc phải kèm theo:
  1. Mục Case mới trong `docs/farm-automation-cases.md`.
  2. Golden XML dump thu thập từ thiết bị thật trong `tests/golden/profile/`.
- **R3 & R4 (Immutability & Ratchet):** 
  - File `expected.json` và `dump.xml` cũ là bất biến (immutable), không được phép sửa hay xóa.
  - Bộ test golden chỉ được phép mở rộng, không được phép thu hẹp (`len(CASES) >= MIN_CASES`).
  - `tests/golden/profile/MANIFEST.lock` chỉ cho phép **APPEND** thêm dòng băm SHA-256 của `expected.json` mới; nghiêm cấm sửa đổi hoặc xóa các hash đã có trong commit `HEAD`.
- **R5 (Case Documentation):** Mục case tài liệu hóa trong `docs/farm-automation-cases.md` bắt buộc chứa 3 trường định danh:
  - `Layout:` (ví dụ `Layout: top_left_pencil` hoặc `Layout: _negative/...`)
  - `Fixture:` (đường dẫn tới `tests/golden/profile/.../dump.xml`)
  - `Anti-pattern:` (mô tả lỗi nhận diện hoặc bẫy sai lệch)

---

## 3. Quy trình thực thi chuẩn hóa khi sửa `profile_layouts` (A-to-Z Contract)

Mỗi khi phát sinh thay đổi trong `profile_layouts/`, Coordinator và Worker bắt buộc phải chuẩn bị đồng thời 4 hạng mục sau trong cùng 1 changeset trước khi commit:

### Bước 1: Patch code logic & Unit test
- Cập nhật file trong `scripts/tiktok_workflow/profile_layouts/`.
- Chạy offline pytest với môi trường cô lập:
  `python -c "import os, sys, subprocess; env=os.environ.copy(); env.pop('PYTHONPATH', None); env.pop('PYTHONHOME', None); sys.exit(subprocess.run([r'D:\CodexRuntime\tiktok-video\venv-core024\Scripts\pytest.exe', 'tests/test_avatar_edit_and_milestone.py'], cwd=r'D:\Taadaa\Tiktok-video', env=env).returncode)"`
  Bắt buộc đạt `34/34 PASSED`.

### Bước 2: Tạo Golden Fixture mới
- Tạo thư mục ca kiểm thử: `tests/golden/profile/<layout>/<case_name>/`.
- Lưu file `dump.xml` từ XML hiện trường máy thật (ví dụ `tests/golden/profile/_negative/m04_add_friends/dump.xml` hoặc `top_left_pencil/m04_.../dump.xml`).
- Tạo file `expected.json` tương ứng:
  ```json
  {
    "layout": "UNKNOWN_LAYOUT",
    "edit_target": null,
    "case_id": "CASE-UI-XX",
    "captured_from": "device-04-add-friends-icon",
    "note": "Top-left add friends icon must be rejected by top_left_pencil layout"
  }
  ```
  *(Đối với ca dương: `"layout": "<layout_name>"`, `"edit_target": {"x": ..., "y": ..., "tolerance": 30}}`)*

### Bước 3: Cập nhật MANIFEST.lock (Ratchet Append-Only)
- Tính mã băm SHA-256 của file `expected.json` vừa tạo (lưu ý chuẩn hóa xuống dòng newline):
  ```python
  import hashlib, pathlib
  p = pathlib.Path("tests/golden/profile/<rel_path>/expected.json")
  h = hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
  rel = str(p.relative_to("tests/golden/profile")).replace("\\", "/")
  line = f"{h}  {rel}\n"
  with open("tests/golden/profile/MANIFEST.lock", "a", encoding="utf-8") as f:
      f.write(line)
  ```
- Kiểm tra toàn vẹn golden: chạy `pytest tests/test_profile_golden.py` (yêu cầu `19/19 PASSED`, không vi phạm manifest tampering).

### Bước 4: Cập nhật tài liệu Case trong `docs/farm-automation-cases.md`
- Thêm đề mục Case tương ứng vào cuối tài liệu với đầy đủ các trường:
  ```markdown
  ### Case 105 (CASE-UI-14): Khử va chạm nút 'Thêm bạn bè' góc trái và chuẩn hóa thứ tự ưu tiên RightPencil > TopLeftPencil

  - **Mã định danh:** `CASE-UI-14` (Máy 4 - Icon Thêm bạn bè góc trên bên trái)
  - **Layout:** `_negative/m04_add_friends` (phân loại âm: `UNKNOWN_LAYOUT`)
  - **Fixture:** `tests/golden/profile/_negative/m04_add_friends/dump.xml`
  - **Hiện tượng lỗi / Yêu cầu vận hành:**
    - ...
  - **Nguyên nhân cốt lõi & Anti-Pattern:**
    - Anti-pattern: ...
  - **Giải pháp & Kiểm chứng:**
    - ...
  ```

### Bước 5: Chạy Preflight Guard & Commit
- Chạy kiểm tra guard trước: `python tools/guard_selector_change.py`
  Bắt buộc xuất hiện: `SELECTOR_GUARD PASSED: All layout selector changes conform to architecture.`
- Thực hiện commit với tiền tố `[L2-surgery]` hoặc scoped commit message.
