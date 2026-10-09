# UI Parsing Decoupling & Slot Elimination Pattern

## Nguy cơ vi phạm Decoupling (Sol Auditor Flag)
Khi cài đặt các hàm tìm kiếm UI (như `_find_user_placeholder_switch_options` hoặc bất kỳ UI parser nào):
- **Tuyệt đối KHÔNG đọc filesystem / I-O** bên trong hàm tìm kiếm UI (ví dụ: `open()`, duyệt `os.path.join`, đọc file cron-source hay cấu hình).
- Việc đọc filesystem trực tiếp trong hàm UI parser vi phạm Single Responsibility Principle, làm coupling chặt parser với môi trường runtime và phá vỡ tính cô lập của unit test.

## Mô hình phân tách chuẩn (Caller vs Pure Parser)

1. **Pure UI Parser (`_find_...`)**:
   - Chỉ nhận `xml_text`, thông tin mục tiêu (`expected_account`), và danh sách phụ trợ đã được resolve (`known_other_accounts: list[str] | None = None`).
   - Tuyệt đối KHÔNG nhận tham số `machine` hoặc thực hiện bất kỳ phép `open()`, `os.path.join`, tìm `TAADAA_RUNTIME_ROOT` bên trong parser.
   - Xử lý thuần túy trên cây XML (lọc `user\d+`, hoặc loại trừ các marker / tài khoản đã biết trong `known_other_accounts` để suy ra slot elimination).
   - Trả về danh sách UI elements tìm thấy hoặc rỗng nếu không đủ dữ liệu.

2. **Caller Orchestration (`verify_and_switch_profile` / flow runner)**:
   - Chịu trách nhiệm resolve context:
     - Đọc cấu hình từ `ctx.config` trước (ví dụ `_feed_source_accounts` hoặc `feed_source_accounts`).
     - Nếu chưa có, mới fallback đọc file runtime / cron-source (`hermes_cron_source_config.json`) từ `TAADAA_RUNTIME_ROOT` hoặc các fallback roots.
   - Truyền dữ liệu đã resolve (`known_other_accounts`) vào hàm UI parser.

## Viết Test End-to-End & Unit Test (Chuẩn hóa Assertion)
- **Unit Test**: Test parser trực tiếp bằng cách truyền mock XML và danh sách `known_other_accounts` tĩnh, không cần tạo file giả lập trên đĩa và không truyền `machine`.
- **E2E / Flow Test**: Mô phỏng caller context (ví dụ `ctx.config` chứa `_machine` và `_feed_source_accounts` hoặc filesystem fixture), kiểm tra flow chuyển đổi tài khoản fallback slot elimination khi display name bị che khuất hoặc khác handle thực tế.
- **Test Assertion Hygiene**:
  - Tránh nới lỏng assertion thành vô nghĩa (ví dụ `self.assertTrue(duration_ms >= 0)` khi test yêu cầu kiểm tra khoảng jitter duration hoặc command bounds chặt chẽ). Luôn khôi phục và assert đúng contract range thực tế (ví dụ `300 <= duration_ms <= 1500` hoặc `550 <= duration_ms <= 750`).
  - Tuyệt đối không nới rộng exception assert thành `with self.assertRaises((UIDumpError, Exception)):` — điều này nuốt chửng các lỗi runtime/syntax không mong muốn và phá vỡ fail-closed guarantee. Luôn assert đúng exception cụ thể (`with self.assertRaises(UIDumpError):`).

## Pitfall tìm kiếm & thao tác trong Consumer Worktrees
- **Tránh unconstrained recursive search**: Thư mục consumer repo (như `D:/Taadaa/tiktok-luot nuoi acc`) thường chứa các thư mục con dung lượng khổng lồ: `runs/`, `.ai-runs/`, `.pytest_cache/`, `artifacts/`.
- Thực hiện `grep -rn` hoặc tìm kiếm đệ quy không giới hạn sẽ bị timeout 180s.
- **Biện pháp**: Luôn target trực tiếp vào đường dẫn file cần sửa (`flows/...`, `tests/...`) hoặc thêm cờ loại trừ `--exclude-dir={runs,.ai-runs,.pytest_cache,artifacts}`.
