# Worker Routing by Latency & Reasoning Effort (Native CLI vs Proxy Pool)

## 1. Phân loại theo Tốc độ & Kênh Điều phối
Từ kết quả benchmark đối đầu 5 hiệp trên Phone Farm (`Gemini 3.8 Flash Medium`):

- **Tier Tốc độ Cao (Fast-Loop Coding / O(1) Fix):**
  - **Công cụ:** Native Headless CLI (`AGY CLI` via `ag_cli.py`, `Haiku CLI` via `claude_worker.py`).
  - **Độ trễ:** ~**3.2s – 5.2s** (gRPC / binary trực tiếp).
  - **Khi nào dùng:**
    * Task sửa code hiện trường $O(1)$ (< 15 dòng, 1 file).
    * Debug và sửa lỗi fail test tức thì (< 30s verify).
    * Cần kết quả nhanh để Coordinator không bị treo context hoặc timeout.

- **Tier Tải Lớn & Không Quota (Heavy Workload / Batch Pool):**
  - **Công cụ:** OmniRoute Pool (`Argon` - `gemini-web-argon-pool`, `Sol` - `gpt-web-sol`).
  - **Độ trễ:** ~**13.5s – 23.8s** (Proxy 4G Mobi + OmniRoute Router + Upstream SSE).
  - **Khi nào dùng:**
    * Cày cuốc tài liệu dài, đọc log kích thước lớn.
    * Refactor code trên diện rộng, viết script mới hoàn toàn.
    * Tác vụ chạy nền (background tasks) không yêu cầu phản hồi theo từng giây.
    * Tận dụng 100% tài nguyên miễn phí (0đ quota IDE/API).

## 2. Kỷ luật Reasoning Effort cho Worker
- **Tránh Deepest Thinking cho Worker:** Ép thinking tối đa làm model suy diễn quá đà, dễ vi phạm nguyên tắc chống over-engineering của Farm và tăng độ trễ lên gấp đôi.
- **Mức tối ưu:** Luôn cấu hình Worker ở mức **`Medium / Standard`** (đủ thông minh cho logic, giữ code gọn gàng, phản hồi nhanh).
