# Quy trình Phục hồi Tài khoản Hết hạn & Bản chất Tier Business (Standard) trong OmniRoute

## 1. Bản chất Nhãn "Business" (Màu vàng) trên OmniRoute
- **Hiển thị giao diện**: Mã nguồn frontend OmniRoute (`ProviderLimits/utils.tsx`) ánh xạ từ khóa `"STANDARD"` sang `{ key: "business", label: "Business", variant: "warning" }`.
- **Bản chất tier**: Đây là các tài khoản Google cá nhân được kích hoạt theo luồng `standard-tier` của Antigravity/Code Assist.
- **Hiện tượng "Không bao giờ tụt quota"**:
  - Combo `ag-gemini-pool-3` chạy theo chiến lược `priority` hoặc `reset-aware`.
  - Toàn bộ tài khoản Pro (`g1-pro-tier`) được xếp ở thứ tự ưu tiên cao nhất (`priority` 1..15).
  - Các tài khoản `standard-tier` (Business) nằm ở nhóm thứ tự ưu tiên phía sau (`priority` 16..31).
  - Do đó, tài khoản Business chỉ nhận request khi các tài khoản Pro bên trên dính rate-limit/429. Trạng thái quota đứng yên là do ít bị routing chạm tới, không phải tài khoản bất tử.
- **Cách kiểm tra liveness thực tế**:
  - KHÔNG dựa vào nút "Test Connection" trên web OmniRoute (nút này dùng probe tối giản thiếu header context thực tế nên dễ trả về 400/401 giả).
  - Kiểm tra bằng request chat completions trực tiếp có gắn header `x-omniroute-connection-id: <cid>`.

## 2. Quy trình Khi Tài khoản Bị "Expired" hoặc Nghi Ngờ Die
- **CẤM TUYỆT ĐỐI**: Tự ý xóa hoặc gỡ connection ra khỏi combo của OmniRoute khi chưa có lệnh của User.
- **Bước 1: Check Live qua web checkmail.live**:
  - Chạy script kiểm tra live web nằm ngay trong repo GPM: `D:/Taadaa/GPM auto/scripts/run_checkmail_kibe_farm.py`.
  - Công cụ dùng Playwright điều khiển Chromium Core 142 của GPM, tự động điền danh sách email vào CodeMirror của `checkmail.live` và bấm Check.
- **Bước 2: Phân loại kết quả**:
  - Nếu email trả về `DIE` / `DISABLED`: Báo cáo user để dọn dẹp hoặc thay thế.
  - Nếu email trả về `LIVE`: Mở profile GPM tương ứng và chạy lại luồng OAuth để làm mới Access Token / Refresh Token.
