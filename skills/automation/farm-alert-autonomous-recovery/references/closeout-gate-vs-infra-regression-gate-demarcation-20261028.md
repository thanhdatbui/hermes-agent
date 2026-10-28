# Phân Định Closeout Gate vs Protection Regression Gate (28/10/2026)

## 1. Hiện Tượng Ảo Giác
Khi người dùng hỏi về các lớp cổng bảo vệ lúc chốt phiên (`done`, `chốt phiên`, `xong phiên`):
- AI Coordinator dễ nhầm lẫn gộp `infra_regression_gate.py` vào quy trình chốt phiên của repo.
- Thực tế người dùng sẽ chất vấn ngay: *"Ủa chứ có thấy bước nào chạy protection regression gate đâu nhỉ"*.

## 2. Bản Chất & Phân Định Hai Cổng

### A. Closeout Gate (`D:/Taadaa/tools/closeout_gate.py` / `closeout_v2.py`)
- **Mục tiêu:** Chống regression nghiệp vụ trong Git repository khi hoàn tất code/task.
- **Quy trình thực thi:**
  1. Tự động phát hiện và chạy test suite trọng tâm của repo (`pytest tests/`, `npm test`...). Nếu test fail -> lập tức REJECT.
  2. Độc lập thẩm định `git diff` (qua Reviewer OmniRoute `:20129` hoặc deterministic `py_compile`).
- **Tuyệt đối:** KHÔNG gọi, không import `infra_regression_gate.py`.

### B. Infrastructure Regression Gate (`D:/Taadaa/tools/infra_regression_gate.py`)
- **Mục tiêu:** Bảo vệ các bất biến hạ tầng máy chủ & Hermes/OmniRoute (heap pressure, retry headroom, port 20129, proxy fail open, SQLite bloat).
- **Phạm vi kích hoạt:**
  - Được tích hợp ĐỘC QUYỀN trong `manage_hermes_config.py` khi có thao tác mutate `config.yaml`.
  - Chạy thủ công độc lập khi kiểm toán hạ tầng.
  - HOÀN TOÀN TÁCH RỜI khỏi luồng `closeout_gate.py` của các repo nghiệp vụ (TikTok, Farm, Gmail...).

## 3. Quy Tắc Trả Lời & Ứng Xử Cho Coordinator
- Khi giải thích hoặc thực thi đóng phiên: Chỉ báo cáo về `closeout_gate.py` (focused pytest chống regression logic code + AI Reviewer / deterministic scorecard).
- Không tự ý bịa thêm `infra_regression_gate` vào quy trình chốt phiên của repo.
