# Upstream Model ID Discipline & Multi-Proxy Failover in OmniRoute

## 1. Upstream Model ID & OmniRoute Codebase Discipline
- **Giữ nguyên model ID chính thức upstream:**
  - Đối với Google Antigravity backend, model ID hợp lệ là: `antigravity/gemini-3.8-flash-tiered`.
  - **CẤM TUYỆT ĐỐI:** Tự ý bịa thêm hậu tố không có trong spec hệ thống (ví dụ tự chế `gemini-3.8-flash-high`) rồi gán vào payload combo hoặc DB.
- **CẤM chọc sửa source core & rebuild bừa bãi:**
  - Không được tùy tiện sửa các file TypeScript trong `open-sse/config/` (`antigravityModelAliases.ts`, `agyModels.ts`, `modelSpecs.ts`) rồi chạy `npm run build` trên production service đang chạy.
  - Việc rebuild đột ngột làm gián đoạn toàn bộ proxy pool, gây downtime và sập hàng loạt kết nối client.
  - Mọi thao tác cấu hình model/combo phải thông qua API chuẩn (`/api/combos`, `/api/providers`) hoặc can thiệp SQLite an toàn, sau đó kiểm tra probe request cô lập trước khi áp dụng.

## 2. OpenCode Free Rotation & Fallback Balancing (Cân bằng tốc độ vs Xoay Proxy)
- **Phân loại lỗi:**
  - **Lỗi nghẽn IP / Rate Limit (429, Connection Timeout, Connection Reset):** Xoay proxy để thử egress IP khác.
  - **Lỗi Model / Upstream Server Hỏng (5xx, 400 Bad Request / Empty Rejection):** Upstream model bị sập hoặc gặp lỗi logic máy chủ. Việc đổi sang proxy khác sẽ vẫn bị lỗi tương tự.
- **Quy tắc Capping Retry (Giới hạn số lần xoay proxy):**
  - Không duyệt tuần tự qua toàn bộ danh sách proxy lớn (ví dụ 68 proxy) vì sẽ gây treo request hàng phút (68 x 5s timeout > 5 phút).
  - Giới hạn tối đa **3 - 5 lần xoay proxy** khi gặp 429/connection error:
    - Nếu trúng IP thông thoáng $\rightarrow$ hoàn thành request nhanh.
    - Nếu sau 3 - 5 proxy khác nhau vẫn thất bại hoặc gặp lỗi upstream server hỏng $\rightarrow$ lập tức dừng rotation và kích hoạt Combo Fallback để rớt xuống model tiếp theo (`mimo-v2.5`, `big-pickle`...) ngay lập tức.
