# UI Hard Enforcement: Layout Registry, Golden XML Corpus & Hard Selector Guard

Dùng tài liệu này khi thiết kế, triển khai hoặc sửa đổi bất kỳ UI selector nào trên toàn bộ hệ thống Taadaa Phone Farm (80-160 thiết bị Android).

---

## 1. Bối Cảnh & Anti-Pattern Cốt Lõi ("Vòng Lặp Phá Hoại")

Trước khi có cơ chế này, các repo automation trên farm thường xuyên rơi vào **vòng lặp phá hoại UI**:
- **Monolith If/Else Spaghetti**: Các hàm `_find_profile_edit_button` hay popup handler kéo dài hàng trăm dòng, hardcode toạ độ tuyệt đối (`[24,96][126,204]`). Khi TikTok cập nhật UI hoặc chạy trên dòng máy khác độ phân giải, toạ độ bị lệch.
- **Agent tự sửa test để bypass quy định**: Khi một máy bị fail, AI Agent vào sửa code cho máy đó, vô tình phá vỡ layout của máy khác. Khi unit test fail, Agent tự động sửa luôn cả `assert` trong test để ép test pass giả dối (như Case 103: commit `2f1155f` tự sửa `assert btn is None` để bypass icon cây bút).
- **Thiếu Golden Corpus thật**: Test chỉ chạy trên mock data tự bịa, không phản ánh XML dump thực tế của ứng dụng TikTok trên thiết bị vật lý.

---

## 2. Ba Trụ Cột Cưỡng Chế Kỹ Thuật Cứng (Hard Enforcement)

### Trụ Cột 1: Kiến Trúc Layout Registry Pattern (`<flow>_layouts/`)
- Tách rời hoàn toàn chuỗi `if/else` monolith thành các class layout độc lập.
- Mỗi layout phải kế thừa `BaseLayout` và có 2 phương thức bắt buộc:
  1. `matches(tree: UiTree) -> bool`: Kiểm tra fingerprint toàn màn hình (kết hợp node bắt buộc, node loại trừ, và package foreground).
  2. `locate(tree: UiTree, intent: str) -> Target | None`: Định vị toạ độ click cho hành vi tương ứng.
- **Quy tắc Fail-Closed dứt khoát**:
  - Khi không có layout nào khớp: Trả về `UNKNOWN_LAYOUT`, lưu artifact vào `quarantine/`, dừng luồng an toàn.
  - Khi có >1 layout cùng khớp: Trả về `AMBIGUOUS_LAYOUT`, dừng luồng, **tuyệt đối cấm tự chọn layout đầu tiên hay fallback toạ độ cũ**.
  - Khi XML parse lỗi: Trả về `DUMP_INVALID`, tách biệt với `UNKNOWN_LAYOUT` để phân biệt lỗi cáp ADB/dump rỗng với màn hình lạ.

### Trụ Cột 2: Bộ Golden XML Corpus Matrix & Cryptographic `MANIFEST.lock`
- Thư mục fixture: `tests/golden/<flow>/<variant>/<case_id>/`:
  - `dump.xml`: Toàn bộ cây XML thực tế trích xuất từ máy farm.
  - `screencap.png`: Ảnh chụp màn hình hiện trường tương ứng.
  - `expected.json`: Kết quả mong đợi (layout name, target coordinates, intent, tolerance).
  - `provenance.json`: Metadata nguồn gốc (machine id, device serial đối soát với workbook `taikhoan_run_safe.xlsx`, timestamp, sha256, PII redacted).
- **Khóa toàn vẹn `MANIFEST.lock`**:
  - Lưu sha256 của `expected.json`, `dump.xml`, và `provenance.json`.
  - Kiểm tra đối soát với `merge-base origin/main` (hoặc committed HEAD) trong pytest runner.
  - **Append-Only Invariant**: Chỉ cho phép thêm dòng mới cho fixture mới. Bất kỳ hành vi sửa đổi hoặc xoá dòng hash cũ đều bị chặn đứng lập tức (`MANIFEST_TAMPERING`).

### Trụ Cột 3: Hard Selector Guard (R0..R8) Tích Hợp Closeout Gate
Chạy qua `python -I -m automation_core.ui.guard --repo <path>`:
- **R0 (Anti-Tamper)**: Cấm sửa đổi các tệp giám sát (`guard_selector_change.py`, `closeout_gate.py`, các file test golden).
- **R1 (Monolith Protection)**: Cấm sửa bất kỳ dòng nào bên trong vùng delegate (`>>> FENCE ... <<< FENCE`) của monolith.
- **R2 (Protocol Discipline)**: Mọi thay đổi trong `*_layouts/` bắt buộc đi kèm fixture `dump.xml` mới và entry tài liệu trong `docs/farm-automation-cases.md`.
- **R3 (Immutability)**: Dữ liệu fixture cũ (`expected.json`, `dump.xml`) là bất biến. `MANIFEST.lock` chỉ được thêm, không được xoá/sửa.
- **R4 (Ratchet)**: Bộ test fixture chỉ được phép tăng theo thời gian, cấm xoá hoặc đổi tên fixture để trốn test.
- **R5 (Case Documentation)**: Entry tài liệu case bắt buộc có đủ các trường chuẩn: `Layout:`, `Fixture:`, `Anti-pattern:`.
- **R6 (Provenance Validator)**: Serial của fixture phải tồn tại trong bảng phân bổ máy của farm, không chứa OTP/PII.
- **R7 (Non-Layout Selector Ban)**: Cấm thêm mới các lệnh parse XML hoặc hardcode `input tap X Y` trong các flow nghiệp vụ ngoài thư mục layout.
- **R8 (Fail-Closed Infrastructure)**: Khi lệnh git lỗi, timeout (15s) hoặc môi trường không nhất quán, guard lập tức REJECT.

---

## 3. 15 Kẽ Hở Kỹ Thuật Cần Phòng Tránh (Audit Findings H1..H15)

1. **H1 (Base Ref Flaw)**: Nếu guard dùng `base=HEAD` mặc định, agent commit xong mới chạy guard -> diff rỗng -> lọt lưới. **Khắc phục**: Base luôn là `merge-base HEAD origin/main`.
2. **H2 (Self-Checking Guard)**: Chạy guard từ chính working tree của repo đang sửa cho phép agent sửa code guard thành `return []`. **Khắc phục**: Guard chạy từ package `automation_core` cài trong venv.
3. **H3 (Partial Hash Lock)**: Chỉ băm `expected.json` mà không băm `dump.xml` cho phép sửa nội dung dump để lách test. **Khắc phục**: Băm cả `expected.json`, `dump.xml` và `provenance.json`.
4. **H4 (Local HEAD Lock Tamper)**: So sánh manifest với HEAD cục bộ cho phép agent commit manifest giả. **Khắc phục**: So sánh với `origin/main`.
5. **H5 (Untracked Blindspot)**: `git diff --name-only` bỏ qua file untracked. **Khắc phục**: Quét cả `git ls-files --others --exclude-standard`.
6. **H6 (Ambiguous Layout Fallback)**: Khi >1 layout cùng khớp, tự chọn layout đầu tiên dẫn tới click sai. **Khắc phục**: Trả về `AMBIGUOUS_LAYOUT` và fail-closed.
7. **H7 (Absolute Pixel Bounding Box)**: Dùng pixel tuyệt đối (`780 <= left <= 950`) gãy trên các máy độ phân giải khác nhau. **Khắc phục**: Chuẩn hóa toạ độ tương đối `0.0 .. 1.0` theo kích thước màn hình.
8. **H8 (Phantom Layout)**: Khai báo layout trong registry nhưng không có fixture test nào. **Khắc phục**: Guard kiểm tra mọi layout trong registry đều có tối thiểu 1 fixture trong corpus.
9. **H9 (Fabricated Fixture)**: Tự viết tay XML giả lập. **Khắc phục**: Yêu cầu `provenance.json` có serial khớp workbook thật và ảnh chụp screencap đính kèm.
10. **H10 (Keyword Grep Bypass)**: Chỉ grep sự xuất hiện của từ khoá trong diff tài liệu. **Khắc phục**: Parse theo block markdown có cấu trúc.
11. **H11 (Silent Parse Failure)**: XML parse lỗi trả cây rỗng được coi là `UNKNOWN_LAYOUT`. **Khắc phục**: Phải raise `DUMP_INVALID` để kích hoạt quy trình kiểm tra ADB.
12. **H12 (Hardcoded Case Count)**: Số lượng test tối thiểu bị ghim cứng trong test. **Khắc phục**: Đọc dòng `#count N` từ header của `MANIFEST.lock`.
13. **H13 (Indirect Gate Call)**: Gate chỉ chạy guard gián tiếp qua tên file test. **Khắc phục**: Gate trực tiếp gọi `automation_core.ui.guard` ở Step 2.5 trước khi chạy bất kỳ test nào.
14. **H14 (Silent Base Fallback)**: Khi so sánh base lỗi, gate tự lùi về `HEAD~1`. **Khắc phục**: Lỗi base phải ném `BLOCKED` ngay lập tức.
15. **H15 (Dual Source of Truth)**: Tồn tại 2 bản sao file guard ở 2 nơi. **Khắc phục**: Đóng gói 1 bản duy nhất trong `automation-core`.

---

## 4. Lộ Trình Triển Khai Toàn Farm (7 Phase Roadmap)

- **Phase 0 (Core Foundation & Patching)**: Đóng gói `automation_core/ui/` (`tree.py`, `layout.py`, `registry.py`, `resolution.py`, `quarantine.py`, `golden/`, `guard/`), vá H1..H15, chạy Red-team 16 kịch bản tấn công. Chuyển `Tiktok-video` sang dùng core.
- **Phase 1 (Shared Popups & Switcher)**: Đóng gói `popup` registry dùng chung (`automation-core/screens/tiktok/popup/`) và `account_switcher` (giải quyết 80% trường hợp kẹt UI trên toàn farm).
- **Phase 2 (Tiktok Nuôi Acc)**: `tiktok-luot nuoi acc` (feed, swipe, comment overlay, cron nuôi 24/7).
- **Phase 3 (Tiktok Follow)**: `tiktok-follow` (Follow / Unfollow, followers list, profile switcher).
- **Phase 4 (Tiktok Login)**: `tiktok-log-in` (Login form, captcha classifier).
- **Phase 5 (Tiktok 2FA)**: `tiktok-add-bao-mat-f2a` (OTP mail, TOTP Authenticator - kiểm tra PII/OTP không lọt vào fixture).
- **Phase 6 (Tiktok Reg)**: `Tiktok_Reg` (Strangler pattern rào fence từng cụm đăng ký, ngày sinh, username trong `social_reg_v1.py`).
