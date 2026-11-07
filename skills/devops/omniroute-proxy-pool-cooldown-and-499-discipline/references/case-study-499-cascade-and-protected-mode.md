# Chi tiết Hiện trường Vòng lặp 499 & Case Study OmniRoute

## 1. Case Study Thực tế (2026-11-07)
Trong phiên đối soát dashboard logs OmniRoute (`:20129/dashboard/logs`) cho combo `ag-gemini-pool-3`:

- **Nhóm 499 lặp không ngừng (Unprotected):**
  - Account: `chu*********@******com` (Proxy: `mirotik_10013`) — Latency chém timeout: 18.7s → 19.9s
  - Account: `nat***************@******com` (Proxy: `mirotik_10034`) — Latency chém timeout: 20.0s → 22.7s
  - Hiện trường trên UI: `shield Unprotected`, không có badge warning, không kích hoạt cooldown. Vòng lặp request tiếp tục dồn vào 2 account này.

- **Nhóm tự phục hồi / được cách ly (Protected):**
  - Account: `phu*************************@******com` (Proxy: `mirotik_10034`) — Cùng proxy với `nat...`, bị chém ở 19.9s nhưng mang cờ `shield Protected` -> Hệ thống gắn nhãn `warning ~6m` cách ly tạm thời.
  - Account: `tol***********@******com` (Proxy: `mirotik_10032`) — Mang cờ `shield Protected` -> Đang có nhãn `warning ~13m`, các request sau trả về 200 OK ổn định (Duration 13-14s).
  - Account: `gia***********@******com` (Proxy: `mirotik_10028`) — Đang có nhãn `warning ~5m`.

## 2. Điểm Mấu chốt Rút ra
- 499 là `AbortError` được sinh ra khi timer `targetTimeoutMs` hết hạn trước khi upstream kịp stream response.
- Circuit Breaker của OmniRoute coi 499 là lỗi hủy luồng phía client (`isLocalStreamLifecycleError = true`), do đó không tự động trừ điểm penalty để đưa account vào `cooldown` nếu account ở chế độ `Unprotected`.
- Khi cần chống tình trạng 1-2 account dính proxy lag kéo sập cả chuỗi combo, bắt buộc phải bật `Protected` cho các account trong pool hoặc kiểm soát chất lượng port proxy tương ứng.
