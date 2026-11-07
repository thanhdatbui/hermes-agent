---
name: omniroute-timeout-and-resilience-discipline
description: "Kỷ luật quản trị timeout 3 tầng, xử lý lỗi false 499 cascade và cấu hình cờ bảo vệ Protected trên OmniRoute."
version: 1.0.0
platforms: [windows, linux]
metadata:
  hermes:
    tags: [omniroute, timeout, 499, circuit-breaker, proxy, resilience]
---
# OmniRoute Timeout & Resilience Discipline

Kỷ luật vận hành và chốt chặn kiến trúc cho hạ tầng proxy LLM OmniRoute (`:20129`).

## 1. Bản chất sự cố HTTP 499 lặp lại không ngừng (False 499 Loop)
- **Hiện tượng:** Một số tài khoản cụ thể (ví dụ: `chu...`, `nat...`) liên tục dính lỗi HTTP 499 trên bảng logs OmniRoute (`:20129/dashboard/logs`) mà không được Circuit Breaker đưa vào trạng thái Cooldown/Cách ly.
- **Cơ chế gây lỗi:**
  1. Khi một target model/connection chạy vượt quá `targetTimeoutMs` của combo (ví dụ: bị bóp ở mức 20s–30s) hoặc proxy bị lag tạm thời, timer nội bộ OmniRoute chủ động abort request.
  2. Trong `open-sse/handlers/chatCore.ts`, việc abort do timer bị phân loại nhầm thành lỗi client tự hủy (`499 Request aborted`).
  3. **Lỗ hổng Circuit Breaker:** Vì coi là lỗi phía client (499) chứ không phải lỗi server upstream (5xx hay 429), Circuit Breaker **KHÔNG** phạt penalty hoặc đưa account vào cooldown.
  4. **Bẫy Least-Used:** Các combo dùng thuật toán `Least-Used` (như `ag-gemini-pool-3`) thấy các account này chưa có lỗi upstream ghi nhận (vẫn `Healthy`), lại tiếp tục ưu tiên dồn request mới vào chính chúng $\implies$ Vòng lặp 499 vô tận.

## 2. Điểm nghẽn Cờ Bảo Vệ: `Protected` vs `Unprotected`
- Mỗi connection trên Dashboard Provider (`:20129/dashboard/providers/<provider>`) có cờ `shield Protected` / `Unprotected`.
- Khi mang cờ `Unprotected`, tài khoản bị mất lớp đệm bảo vệ rate-limit & cooldown khi proxy trễ.
- **Khắc phục:** Bắt buộc bật `shield Protected` cho tất cả các connection chạy qua dải proxy quay/remote để khi proxy lag chạm timeout, tài khoản được tự động cách ly (`warning ~5m - 15m`), combo sẽ tự động nhảy qua tài khoản khác mà không bị kẹt lặp lại.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
