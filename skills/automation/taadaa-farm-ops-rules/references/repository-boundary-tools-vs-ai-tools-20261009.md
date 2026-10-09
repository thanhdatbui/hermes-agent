# Repository Boundary Invariant: Taadaa Tools vs AI-Tools (User chốt 2026-10-09)

## 1. NGUYÊN TẮC PHÂN CHIA REPO CHUẨN FARM
- **`D:/Taadaa/tools` (Repo: `taadaa-farm-tools`)**:
  - Chuyên trách: TOÀN BỘ VẬN HÀNH FARM TAADAA.
  - Bao gồm: Script tự động hóa điện thoại, ADB commands, quản lý Proxy (3proxy, singbox, mobiproxy), hạ tầng Wi-Fi (Aruba AP, DHCP), watchdogs hệ thống, cơ chế device_lock, và các file quy chuẩn vận hành (`AGENTS.md`, `PROJECT_RULES.md`).
  - Mọi thay đổi, fix bug hay bổ sung công cụ vận hành farm BẮT BUỘC phải lưu, commit và push về repo này.

- **`D:/Taadaa/AI-Tools` (Repo: `AI-Tools`)**:
  - Chuyên trách: CÁC CÔNG CỤ LINH TINH, OTHER & RESEARCH.
  - Bao gồm: Các script AI research, converter, scraping tiện ích ngoài farm, benchmark mô hình tổng hợp, tooling phụ trợ.
  - Tuyệt đối KHÔNG đẩy script hoặc rule điều khiển farm cốt lõi vào đây để tránh phân mảnh mã nguồn.
