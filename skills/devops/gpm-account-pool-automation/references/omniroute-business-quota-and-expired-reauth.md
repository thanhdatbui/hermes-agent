# Khắc phục Tài khoản Expired & Phân tích Nhãn Business trong OmniRoute

## 1. Bản chất nhãn "Business" màu vàng trên Dashboard OmniRoute (:20129)
- **Mã nguồn hiển thị:** Trong `src/app/(dashboard)/dashboard/usage/components/ProviderLimits/utils.tsx`:
  ```typescript
  if (upper.includes("BUSINESS") || upper.includes("STANDARD") || upper.includes("BIZ"))
      return { key: "business", label: "Business", variant: "warning", rank: 5, raw };
  ```
  Nhãn "Business" kèm cảnh báo vàng (`variant: "warning"`) thực chất là tài khoản Google cá nhân được kích hoạt theo diện `standard-tier` (hạn ngạch developer standard của Google Cloud / Code Assist).
- **Hiện tượng "Không bao giờ tụt Quota":**
  - Trong combo định tuyến (như `ag-gemini-pool-3`), OmniRoute áp dụng chiến lược `priority` hoặc `reset-aware`.
  - Các tài khoản Pro (`g1-pro-tier`) luôn được xếp ở các mức Priority cao nhất (Priority 1 -> 15).
  - Các tài khoản "Business" (`standard-tier`) nằm ở Priority thứ cấp (từ Priority 16 trở đi).
  - Do các tài khoản Pro gánh toàn bộ tải request thông thường, các tài khoản Business hầu như không nhận request hoặc chỉ nhận khi dàn Pro quá tải/429. Việc quota không tụt là do **ít/chưa được gọi tới**, không phải do tài khoản bất tử.

## 2. Quy trình xử lý Tài khoản Expired / Revoked
### QUY TẮC BẢO TOÀN POOL:
- **CẤM TUYỆT ĐỐI** tự ý xóa connection khỏi combo khi phát hiện token hết hạn hoặc lỗi 401 `Token invalid or revoked`.
- Xóa connection làm gãy kiến trúc mapping target của combo và mất dấu tài khoản trong hệ thống.

### BƯỚC 1: Kiểm tra trạng thái LIVE bằng web checkmail.live
- Sử dụng công cụ tự động hóa đã lưu sẵn tại repo `D:\Taadaa\GPM auto\scripts\run_checkmail_kibe_farm.py`.
- Cơ chế hoạt động: Tương tác qua CodeMirror trên web `checkmail.live` bằng Playwright để kiểm tra tài khoản sống/chết (Live / Die / Verify) mà không cần login on-device tránh checkpoint.
- Nếu tài khoản báo `LIVE`: Tiến hành Bước 2.
- Nếu tài khoản báo `DIE`: Báo cáo user trước khi thay thế.

### BƯỚC 2: Mở GPM Profile và Re-OAuth lại
- Tìm profile GPM tương ứng qua API `http://127.0.0.1:19995/api/v3/profiles`.
- Khởi động profile trình duyệt qua GPM Local API.
- Thực hiện lại luồng đăng nhập Google và cấp quyền OAuth Antigravity để lấy refresh token mới.
- Sau khi có token mới, connection trên OmniRoute tự động cập nhật hoặc gọi endpoint update, không làm thay đổi ID connection trong combo.
