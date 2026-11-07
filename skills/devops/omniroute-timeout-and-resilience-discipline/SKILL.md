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

## 3. Invariant Timeout 3 Tầng (3-Layer Timeout Invariant)
Đã được kiểm chứng và đồng thuận bởi Claude CLI & Sol Auditor qua các sự cố 24/09 & 21/10:
$$\mathbf{HERMES\_CLIENT\ (120s)\ >\ COMBO\_TARGET\ (60s)\ >\ STREAM\_READINESS\ (40s)}$$

1. **Tầng 1 (Client Hermes):** `HERMES_API_CALL_STALE_TIMEOUT = 120s`. Đảm bảo client có đủ kiên nhẫn chờ failover hạ cánh an toàn.
2. **Tầng 2 (Combo Failover):** `targetTimeoutMs = 60000` (60s) cho các combo chủ lực (`ag-gemini-pool-3`, `omni-worker`).
   - *Cấm hạ xuống 20s - 30s:* Hạ xuống 20s–30s sẽ xung đột với các request ngữ cảnh lớn (250k–480k tokens) hoặc multimodal vision (ảnh base64 >70k chars), khiến request hợp lệ bị chém nhầm thành 499.
   - *Cấm tăng > 90s:* Tăng quá cao sẽ bão hòa hàng đợi in-flight và gây đơ socket như sự cố ngày 24/09.
3. **Tầng 3 (Stream Readiness / Socket):** `STREAM_READINESS_TIMEOUT_MS = 40000` (40s) trong `.env`. Chém kết nối đơ trước 5s–20s để nhường quyền failover sạch cho tầng Combo.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
