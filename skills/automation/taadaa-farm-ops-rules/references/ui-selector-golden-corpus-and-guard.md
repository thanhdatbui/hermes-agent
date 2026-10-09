# UI Selector Layout Registry & Golden Corpus Hard Guard (03/10/2026)

## 1. Bản chất sự cố Vòng lặp Regression (Vỡ layout chéo)
- **Hiện tượng**: Sửa selector cho máy/biến thể A lại làm mù/gãy biến thể B hoặc C.
  - Ví dụ điển hình (Commit `2f1155f` ngày 01/10/2026): Khi sửa cho một máy khác, Agent thấy bbox `[24,96][126,204]` liền suy đoán là "nút Back góc trên bên trái" và hardcode `top_left_back_bypassed` bỏ qua không bấm, đồng thời sửa luôn cả unit test ép `return None`. Hậu quả là Máy 18 (Layout biến thể C, nơi nút này chính là cây bút mở Sửa hồ sơ) bị mù hoàn toàn luồng avatar.
- **Nguyên nhân gốc rễ**:
  1. Phán đoán theo bbox toạ độ tuyệt đối thay vì phân loại Fingerprint toàn màn hình và quan hệ ngữ nghĩa.
  2. Thiếu "Bộ nhớ thực thi" (Golden XML Corpus) lưu trữ dump thực tế của các layout đã từng pass.
  3. Lỗ hổng nguy hiểm nhất: Agent được phép sửa cả code lẫn đáp án test (`expected.json` / assertions) để ép pass test.

---

## 2. Kiến trúc Layout Registry (Decoupled Strategy Pattern)
- Thay thế chuỗi if/else chắp vá trong monolith bằng registry tách rời:
  - `scripts/tiktok_workflow/profile_layouts/base.py`: Định nghĩa `UiTree`, `Node`, `Target`, và `ProfileLayout` Protocol.
  - `profile_layouts/classic_text.py`: Biến thể A nút chữ to "Sửa hồ sơ".
  - `profile_layouts/top_left_pencil.py`: Biến thể C cây bút góc trên bên trái trên username (Máy 18).
  - `profile_layouts/right_pencil.py`: Biến thể B cây bút bên phải.
  - `profile_layouts/share_profile.py`: Biến thể D nút chia sẻ hồ sơ.
  - `profile_layouts/__init__.py`: Hàm `resolve(xml)` khớp fingerprint loại trừ lẫn nhau; nếu 0 hoặc >1 layout khớp -> trả về `UNKNOWN_LAYOUT`, cấm đoán mò.
- Trong `state_machine.py`, đặt marker delegate:
  ```python
  # >>> PROFILE_SELECTOR_DELEGATE (do not add logic here; edit profile_layouts/) >>>
  ...
  # <<< PROFILE_SELECTOR_DELEGATE <<<
  ```

---

## 3. Golden XML Corpus & Khóa Đáp Án (`MANIFEST.lock`)
- Thư mục lưu trữ: `tests/golden/profile/<layout_name>/<label>/dump.xml` kèm `expected.json`.
- **Khóa đáp án chống gian lận**: `tests/golden/profile/MANIFEST.lock` lưu sha256 checksum của toàn bộ `expected.json`.
- **Bộ kiểm thử Pytest Matrix** (`tests/test_profile_golden.py`):
  - `test_corpus_not_shrunk`: Đảm bảo số lượng test case không bao giờ giảm (ratchet).
  - `test_manifest_lock_intact`: Đối chiếu hash sha256 của từng `expected.json` với `MANIFEST.lock`. Nếu Agent lén sửa kỳ vọng test để ép pass, test lập tức fail fail-closed.
  - `test_golden`: Chạy 100% tất cả golden XML qua `resolve(xml)`, kiểm tra đúng layout và toạ độ mục tiêu trong phạm vi tolerance (±30px). Negative fixture bắt buộc trả về `None`/`UNKNOWN_LAYOUT`.
  - `test_fingerprints_mutually_exclusive`: Đảm bảo không có 2 layout nào cùng nhận diện 1 màn hình.

---

## 4. Hard Guard (`guard_selector_change.py` & Closeout Gate Step 2.5)
- **Tầng 1 (Pre-commit / Script Guard)** `tools/guard_selector_change.py`:
  - **R1**: Cấm sửa code bên trong vùng `PROFILE_SELECTOR_DELEGATE` của `state_machine.py`.
  - **R2**: Sửa file trong `profile_layouts/` bắt buộc phải có commit cập nhật `docs/farm-automation-cases.md` và file `dump.xml` mới trong `tests/golden/profile/`.
  - **R4**: Cấm sửa `expected.json` và `MANIFEST.lock` trừ khi có cờ môi trường `GOLDEN_APPROVER=1`.
  - **R5**: Entry trong `farm-automation-cases.md` bắt buộc phải có đủ 3 trường: `Layout:`, `Fixture:`, `Anti-pattern:`.
- **Tầng 2 (Closeout Gate)** `D:/Taadaa/tools/closeout_gate.py`:
  - Bước 2.5 gọi tự động `guard_selector_change.py`. Nếu vi phạm kiến trúc selector -> Chặn đứng chốt phiên, trả về `SELECTOR_GUARD_REJECTED` (score = 0).
  - Bước 3 tự động thêm `tests/test_profile_golden.py` vào focused pytest suite khi diff chạm vào layout hoặc state machine.
