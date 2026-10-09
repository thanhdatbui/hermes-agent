# UI Hard Enforcement Pattern: Layout Registry, Golden XML Corpus & Hard Selector Guard

Dùng khi phát triển, sửa lỗi hoặc tái cấu trúc các luồng tương tác UI / ADB trên toàn bộ farm (Tiktok-video, tiktok-follow, tiktok-log-in, tiktok-add-bao-mat-f2a, Tiktok_Reg, automation-core).

## 1. Vấn đề gốc rễ: Vòng lặp phá hoại UI (Regression Loop)
- Trong các script monolith (ví dụ `state_machine.py` >7.000 dòng), các hàm tìm kiếm UI (`_find_profile_edit_button`, `_find_follow_button`) thường chứa chuỗi `if/else` chắp vá toạ độ tuyệt đối.
- Khi một máy gặp biến thể A/B testing mới, AI Agent thường sửa cục bộ:
  1. Nhìn toạ độ một máy rồi suy đoán chủ quan (ví dụ: nhầm icon cây bút góc trên trái thành nút Back, nhầm icon "Thêm người" thành cây bút).
  2. Bypass hoặc gán toạ độ cứng cho máy đó.
  3. Sửa luôn cả unit test thành `assert btn is None` để ép test pass giả dối.
  4. Hậu quả: máy này chạy được thì máy khác bị gãy (`AVATAR_EDIT_OPEN_FAILED`), các lỗi cũ đã fix bị tái diễn.

## 2. Kiến trúc 4 Trụ Cột Cưỡng Chế Kỹ Thuật Cứng (Hard Enforcement)

### Trụ cột 1: Layout Registry Pattern (`<screen>_layouts/`)
- Tách rời hoàn toàn chuỗi `if/else` khỏi file monolith sang thư mục layout riêng.
- Mỗi biến thể giao diện là một class độc lập kế thừa `BaseLayout`:
  - `fingerprint(tree)`: Phân loại dựa trên đặc trưng toàn màn hình (presence của text/id, absence của các nút xung đột, package foreground).
  - `locate(tree, intent)`: Trả về `Target(x, y)` hoặc toạ độ chuẩn hoá tương đối.
- **Fail-Closed dứt khoát**: Khi `resolve()` không khớp layout nào:
  - Trả về `UNKNOWN_LAYOUT` (hoặc `AMBIGUOUS_LAYOUT` nếu >1 layout cùng khớp).
  - Tự động dump XML + screencap lưu vào thư mục cách ly `quarantine/<screen>/<date>/`.
  - Dừng luồng an toàn, phát metric `unknown_layout_quarantined`.
  - **TUYỆT ĐỐI CẤM** fallback đoán mò toạ độ cũ hoặc click bừa.

### Trụ cột 2: Golden XML Corpus Matrix (`tests/golden/<screen>/`)
- Lưu trữ các XML dump thực tế thu thập từ máy thật:
  - Cả **Positive fixtures** (mỗi layout variant có ít nhất 1 dump thật).
  - Cả **Negative fixtures** (màn hình feed, settings, dialog hệ thống, hoặc màn hình dễ nhầm lẫn như "Thêm người" trên Máy 40).
- Mỗi fixture gồm `dump.xml`, `expected.json`, và `provenance.json` (device_id, serial đối soát với workbook, timestamp, sha256).

### Trụ cột 3: Cryptographic `MANIFEST.lock` (Chống Agent sửa test)
- File `MANIFEST.lock` lưu mã băm SHA256 của toàn bộ `expected.json` và `dump.xml`.
- Bộ test pytest matrix (`test_profile_golden.py`):
  - Tự động đối soát checksum trong `MANIFEST.lock` với commit HEAD trong git.
  - Nếu Agent tự ý sửa `expected.json` để ép test pass, pytest lập tức ném lỗi vi phạm tính toàn vẹn (Integrity Failure) và chặn commit.
  - Cơ chế **Ratchet**: Fixture chỉ được phép tăng (append-only), cấm tuyệt đối xóa hoặc đổi tên fixture cũ.

### Trụ cột 4: Hard Selector Guard (`guard_selector_change.py` / Closeout Gate)
- Được kích hoạt tự động tại Step 2.5 của `closeout_gate.py`:
  - **R0 (Anti-Tamper)**: Cấm sửa đổi `guard_selector_change.py`, `closeout_gate.py`, file test golden, file test guard.
  - **R1 (Monolith Fence)**: Cấm sửa bất kỳ dòng nào bên trong vùng `PROFILE_SELECTOR_DELEGATE` của file monolith.
  - **R2 (Protocol Discipline)**: Sửa code layout bắt buộc phải có entry trong `docs/farm-automation-cases.md` và golden dump fixture thật mới.
  - **R3 (Immutability)**: Cấm sửa `expected.json` / `dump.xml` có sẵn. `MANIFEST.lock` chỉ cho phép thêm dòng hash mới, cấm xóa/sửa hash cũ.
  - **R4 (Ratchet)**: Cấm xóa hoặc đổi tên fixture golden.
  - **R5 (Case Documentation)**: Bắt buộc tài liệu case phải có đủ các trường `Layout:`, `Fixture:`, `Anti-pattern:`.
  - **R8 (Fail-Closed Infrastructure)**: Git command timeout (15s) hoặc exception bắt buộc trả `GIT_ERROR` và REJECT, tuyệt đối cấm silent pass.

## 3. Quy trình Độc lập Thẩm định & Review Loop (Claude Code CLI / Sol Auditor)
- Khi user phát lệnh "Làm đi cho claude duyệt thì thôi" / "chấm đến khi đạt":
  - **CẤM DỪNG LẠI** khi Reviewer trả về `REJECT` / `CHANGES REQUESTED` để hỏi xin phép.
  - Đây là vòng lặp tự sửa chữa khép kín (Autonomous Remediation Loop):
    1. Đọc kỹ từng finding cụ thể của Reviewer.
    2. Sửa code, siết chặt guard, bổ sung test/fixture thực tế.
    3. Chạy focused tests pass 100%.
    4. Re-invoke Reviewer cho tới khi đạt phán quyết `APPROVED` chính thức.

## 4. Kỷ luật Vận hành: Không vội nhân rộng khi chưa nướng đủ thời gian thực tế
- Khi vừa giải quyết xong một lỗi UI lớn trên 1 máy/1 repo và xây dựng cơ chế mới:
  - **KHÔNG vội vàng mổ xẻ nhân rộng ngay lập tức ra toàn bộ các repo khác (`automation-core`, `tiktok-follow`, `f2a`...).**
  - Hãy để script vừa fix chạy thực tế trong 1–2 ca làm việc trên đàn máy thật để quan sát telemetry (`layout_resolved` vs `unknown_layout_quarantined`) và thu thập thêm XML dump thật.
  - Việc mở nhiều mặt trận cùng lúc khi chưa kiểm chứng thực chiến sẽ làm phân tán context và tăng rủi ro lỗi dây chuyền trên farm.
