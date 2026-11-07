---
name: omniroute-proxy-pool-cooldown-and-499-discipline
description: "Kỷ luật chẩn đoán lỗi 499 lặp vô tận (false abort), đối soát cờ Protected vs Unprotected trên OmniRoute, và quy trình phân lập nghẽn proxy."
version: 1.0.0
tags: [omniroute, proxy, 499, circuit-breaker, cooldown, protected-mode]
---
# OmniRoute Proxy Pool Cooldown and 499 Discipline

## 1. Triệu chứng Hiện trường
- Trên OmniRoute Dashboard (`:20129/dashboard/logs`), một số account bị lỗi `499 Request aborted` hoặc `[499] Client disconnected` lặp lại liên tục, trong khi các account khác cũng dính 499 nhưng tự phục hồi được hoặc được cách ly tạm thời (`warning ~Xm`).
- Lỗi 499 thường có duration tập trung quanh mốc timeout (~18s–23s hoặc ~30s).
- Account bị 499 liên tục KHÔNG chuyển sang trạng thái cooldown/warning mà tiếp tục nhận traffic rồi fail tiếp.

## 2. Cơ chế Kỹ thuật

### A. Bản chất mã lỗi HTTP 499
- Khi upstream fetch bị timeout (hoặc proxy nghẽn khiến request kéo dài vượt quá `targetTimeoutMs`), internal controller throw `AbortError`.
- Trong `open-sse/handlers/chatCore.ts`, `isLocalStreamLifecycleError()` coi đây là client tự hủy kết nối (`isRequestAborted = true`) và ghi mã HTTP `499`.
- **Cơ chế Circuit Breaker:** Vì bị coi là lỗi do client abort (499) chứ không phải lỗi do upstream provider sập (502/503/429), Circuit Breaker **KHÔNG** tính điểm phạt (penalty) để đưa account vào trạng thái Cooldown.
- Kết quả: Account vẫn ở trạng thái `Healthy`, Combo Router tiếp tục route request vào nó -> tạo thành vòng lặp 499 vô tận.

### B. Cờ "Protected" vs "Unprotected" trên Provider Connections
- Trên giao diện `/dashboard/providers/<provider>` (ví dụ `antigravity`), mỗi connection có cờ bảo vệ:
  - **`Protected`**: Được áp dụng policy giới hạn lỗi nghiêm ngặt hơn hoặc khi dính kèm theo một lỗi upstream (5xx, 429, hoặc breaker probe fail), account được gắn cờ `warning ~Xm` (cách ly tạm thời từ 5-15 phút). Trong thời gian này, Combo Router bỏ qua account đó, giúp nó không bị spam dồn dập và có thời gian xả nghẽn proxy/hồi phục quota.
  - **`Unprotected`**: Không được cách ly tự động khi dính chuỗi 499 (do 499 bị coi là client error vô hại). Nếu proxy gắn với account này bị chậm (>20s), mọi request đổ vào account đều chạm timeout, sinh lỗi 499 liên tục mà không bao giờ được nghỉ.

### C. Vai trò của Proxy Binding (`mirotik_XXXXX`)
- Khi một port proxy (ví dụ `mirotik_10034`) bị nghẽn mạng:
  - Account `Protected` gán vào port đó: Gặp lỗi sẽ được cách ly nghỉ 5-15m (`warning ~6m`).
  - Account `Unprotected` gán vào port đó: Tiếp tục bị chọn trong round-robin / least-used, sinh 499 liên tục.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
