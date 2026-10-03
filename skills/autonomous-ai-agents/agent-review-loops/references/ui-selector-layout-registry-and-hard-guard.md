# UI Selector Layout Registry & Hard Anti-Tamper Guard Pattern

Tài liệu hướng dẫn triển khai cơ chế chống phá vỡ selector UI trên hệ thống automation farm thiết bị (Android/TikTok/GPM), giải quyết triệt để vấn nạn AI coding agent tự ý sửa test để ép pass ("chữa test thay vì chữa code").

## 1. Bản Chất Vấn Đề (Anti-Pattern Lặp Lại)

Trong các codebase monolith lớn (>1500 dòng), logic định vị phần tử UI (button, input, avatar, switch) thường bị dồn vào chuỗi `if/else` spaghetti dài hàng trăm dòng. Khi gặp một biến thể giao diện mới trên máy thật:
- **Lỗi 1 (Ad-hoc Bounding Box Guessing):** Agent tự nhìn toạ độ màn hình máy đó và hardcode thêm một nhánh `left >= 20 and top >= 90...` mà không xét fingerprint toàn màn hình, gây false positive đè lên các nút khác ở màn hình khác (ví dụ: nhầm nút Thêm bạn `[24,96][132,204]` thành cây bút Sửa hồ sơ `[24,96][126,204]`).
- **Lỗi 2 (Tampering Unit Tests):** Khi selector mới làm gãy unit test cũ, agent tự tiện sửa code unit test (ví dụ đổi `assert btn is not None` thành `assert btn is None`) để ép toàn bộ test suite xanh mướt (fake green) nhằm vượt qua pre-commit hook.
- **Lỗi 3 (Doc Mềm Vô Tác Dụng):** Các quy tắc ghi trong file tài liệu (`AGENTS.md`, `docs/cases.md`) chỉ là hướng dẫn mềm (soft guidance), LLM agent hoàn toàn có thể bỏ qua khi bị áp lực hoàn thành task.

---

## 2. Giải Pháp 4 Trụ Cột (Hard Enforcement Architecture)

### Trụ Cột 1: Kiến Trúc Layout Registry Pattern (`profile_layouts/`)
Tách rời hoàn toàn chuỗi `if/else` khỏi monolith thành các strategy độc lập:
- **Base Protocol (`base.py`):**
  ```python
  class ProfileLayout(Protocol):
      name: str
      def matches(self, tree: UiTree) -> bool: ...
      def locate_edit(self, tree: UiTree, adapter: Optional[object] = None) -> Optional[Target]: ...
  ```
- **Từng biến thể riêng biệt:**
  - `classic_text.py`: Nút chữ to chuẩn ("Sửa hồ sơ", "Edit profile").
  - `top_left_pencil.py`: Cây bút góc trên bên trái trên username (kèm điều kiện loại trừ dứt khoát "Thêm người", "Quay lại", "Menu").
  - `right_pencil.py`: Cây bút bên phải.
  - `share_profile.py`: Nút chia sẻ.
- **Fail-Closed dứt khoát trong Monolith:**
  Trong `state_machine.py`, monolith chỉ đóng vai trò delegate:
  ```python
  # >>> PROFILE_SELECTOR_DELEGATE (do not add logic here; edit profile_layouts/) >>>
  @staticmethod
  def _find_profile_edit_button(adapter, xml_text: str) -> Optional[dict]:
      try:
          from .profile_layouts import resolve
          res = resolve(xml_text, adapter=adapter)
          if res.target:
              return {"center": (res.target.x, res.target.y)}
          logger.warning("[PROFILE_EDIT] [METRIC] event=unknown_layout_quarantined matched=%s", res.matched)
      except Exception as e:
          logger.error("[PROFILE_EDIT] Layout resolution error: %s", e)
      return None
  # <<< PROFILE_SELECTOR_DELEGATE <<<
  ```
  Nếu không khớp layout nào: trả về `None`, phát metric `event=unknown_layout_quarantined` và dừng luồng an toàn. **Cấm tuyệt đối fallback đoán mò toạ độ.**

---

### Trụ Cột 2: Bộ Golden XML Corpus Matrix (`tests/golden/`)
Xây dựng thư mục chứa dữ liệu UI dump thực tế thu thập từ máy thật:
- Mỗi fixture gồm 2 file: `dump.xml` (dump uiautomator thật) và `expected.json`:
  ```json
  {
    "layout": "top_left_pencil",
    "edit_target": {"x": 75, "y": 150, "tolerance": 30},
    "case_id": "CASE-UI-12",
    "captured_from": "device-18",
    "note": "Top-left pencil icon above username opens ProfileEditActivity"
  }
  ```
- **Bắt buộc có Fixture Âm (Negative Fixtures):**
  - Màn hình lướt video For You (`_negative/feed_screen/`): `expected.json` ghi `"layout": "UNKNOWN_LAYOUT", "edit_target": null`.
  - Màn hình có phần tử tương tự nhưng khác vai trò (`_negative/m40_them_nguoi/`): Chứng minh selector không bị false positive khi gặp icon ở cùng toạ độ nhưng mang ý nghĩa khác.
- **Chuẩn Hóa XML Thu Thập Từ ADB:**
  Lệnh `adb shell uiautomator dump` thường in dòng prefix `UI hierchary dumped to: /data/local/tmp/uidump.xml` ở đầu file. Bắt buộc cắt bỏ dòng này trước khi lưu vào golden corpus để XML parser đọc hợp lệ.

---

### Trụ Cột 3: Khóa Mã Băm Toàn Vẹn (`MANIFEST.lock`)
- Lưu mã băm SHA256 của toàn bộ `expected.json` và `dump.xml`:
  ```
  <sha256_hash>  tests/golden/profile/top_left_pencil/m18_20261002/expected.json
  <sha256_hash>  tests/golden/profile/classic_text/m01_standard/expected.json
  ```
- **Chống Agent Sửa Cả Lock Lẫn Đáp Án:**
  Trong test runner `test_profile_golden.py`:
  ```python
  def test_manifest_lock_intact():
      # Đối soát trực tiếp với HEAD đã commit trong Git object store
      res = subprocess.run(["git", "show", "HEAD:tests/golden/profile/MANIFEST.lock"], capture_output=True, text=True)
      committed_lock = res.stdout
      # Nếu hash trong working tree khác committed_lock -> Báo lỗi TAMPERING DETECTED ngay lập tức!
  ```
  Vì Agent không thể sửa lịch sử commit Git, việc sửa trộm đáp án test trong working tree sẽ bị bắt quả tang 100%.

---

### Trụ Cột 4: Chốt Chặn Kỹ Thuật Cứng (`guard_selector_change.py`)
Tích hợp trực tiếp vào Pre-commit Hook và `closeout_gate.py` (Step 2.5), kiểm tra 6 luật cứng:

1. **R0 (Anti-Tamper):** Cấm Agent sửa đổi các file cốt lõi: `guard_selector_change.py`, `closeout_gate.py`, `test_profile_golden.py`, `test_guard_selector_change.py`.
2. **R1 (Monolith Protection):** Quét diff của `state_machine.py`. Nếu có bất kỳ dòng thay đổi nào nằm trong khoảng dòng của vùng `PROFILE_SELECTOR_DELEGATE` -> Chặn ngay lập tức. Bắt buộc viết layout trong `profile_layouts/`.
3. **R2 (Protocol Discipline):** Nếu chạm vào `profile_layouts/`, bắt buộc diff phải kèm:
   - Cập nhật tài liệu case trong `docs/farm-automation-cases.md`.
   - Bổ sung file `dump.xml` thực tế từ máy thật trong `tests/golden/`.
4. **R3 (Immutability):**
   - Đổi tên (`R...`) hoặc sửa (`M`) bất kỳ file `expected.json` hoặc `dump.xml` cũ nào đều bị coi là vi phạm và bị chặn.
   - Đối với `MANIFEST.lock`: Chỉ cho phép thêm dòng hash mới (`+`), cấm tuyệt đối xóa hoặc sửa đổi dòng hash cũ (`-`).
5. **R4 (Ratchet Rule):** Cấm xóa (`D`) bất kỳ fixture nào trong `tests/golden/`. Bộ fixture chỉ được phép tăng lên theo thời gian, không bao giờ được giảm đi.
6. **R5 (Case Schema):** File tài liệu case mới bắt buộc phải chứa đủ 3 trường chuẩn hóa: `Layout:`, `Fixture:`, `Anti-pattern:`.

### Quy Tắc Chống Fail-Open Trong Script Guard:
- Mọi lệnh `subprocess.run` trong guard bắt buộc có `timeout=15s`.
- Nếu lệnh git diff gặp timeout hoặc lỗi: Hàm bắt buộc trả về `GIT_ERROR` và thoát với exit code 1 (Fail-Closed). Tuyệt đối không được trả về chuỗi rỗng `""` vì sẽ làm lọt toàn bộ các luật R1..R5.
