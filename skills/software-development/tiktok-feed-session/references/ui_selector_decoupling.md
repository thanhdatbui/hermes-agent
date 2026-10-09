# UI Selector Decoupling & Unit Testing Patterns

## 1. Nguyên Tắc Decoupling UI Selector
- **Selector thuần túy (Pure Selector):** Các hàm phân tích UI element / XML (ví dụ `_find_user_placeholder_switch_options`) không được đọc trực tiếp từ filesystem, không đọc `hermes_cron_source_config.json` hay truy vấn database/môi trường bên ngoài.
- **Dependency Injection:** Mọi dữ liệu phụ trợ (như danh sách tài khoản đã biết khác `known_other_accounts`) phải được truyền vào qua tham số hàm dưới dạng resolve sẵn (`list[str] | None`).
- **Trách nhiệm của Caller:**
  - Caller trong flow (chẳng hạn `verify_and_switch_profile`) có sẵn DeviceContext (`ctx.config`), chịu trách nhiệm trích xuất cấu hình hoặc thông tin runtime và truyền vào selector.

## 2. Viết Unit Test Cách Ly
- Khi selector đã được decouple khỏi filesystem:
  - Unit test chỉ cần cung cấp chuỗi `xml_text` mẫu và các tham số dạng primitive/collection (`known_other_accounts=["acc1", "acc2"]`).
  - Không cần mock `open`, `os.path.exists`, hay giả lập thư mục runtime bên ngoài.
  - Test chạy nhanh, ổn định và không phụ thuộc vào trạng thái máy/môi trường.
