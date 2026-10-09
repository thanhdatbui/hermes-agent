# Antigravity Pro Quota, Large Context Latency & VM Automation Quirks

## 1. Upstream Quota vs "Requests Not Arriving" (Latency Illusion)

### Triệu chứng:
Người dùng hoặc agent chạy subagent/worker qua combo `omni-worker` / `ag-gemini-pool-3` nhưng thấy "không có phản hồi", "treo" hoặc nghi ngờ request không tới được pool Pro.

### Bản chất thực tế (Evidence-based):
1. **Large Context Latency:**
   - Trong các lượt dispatch worker phức tạp, context kéo theo lịch sử session và file contents rất lớn (> 250k - 280k tokens).
   - Gemini xử lý input tokens lớn (280k tokens in) mất trung bình **15s – 25s** per turn (`duration: 20000ms - 25000ms`).
   - Request **thực tế vẫn gửi tới OmniRoute và trả về HTTP 200**, không phải bị drop hay tắc nghẽn.
2. **Upstream Quota Pool Exhaustion & Fallback Latency:**
   - Hầu hết các tài khoản Pro dùng nhiều ngày sẽ cạn quota gia đình Gemini (`used: 990-1000 / 1000`, quota còn < 1%).
   - Khi combo duyệt danh sách (theo thứ tự sticky hoặc priority), các tài khoản cạn quota trả 429 hoặc cooling down, OmniRoute phải fallback 1-2 nhịp sang các tài khoản Pro mới có quota (ví dụ `alicelmoralesjvcrj`, `vuthao04122002a`).
   - Kiểm tra quota chuẩn bằng `GET http://127.0.0.1:20129/api/usage/provider-limits` (xem key `caches[connectionId].quotas`) thay vì phán đoán từ 1 request đơn lẻ.

---

## 2. Nâng cấp Account Free -> Pro trên OmniRoute

Khi nâng cấp gói một tài khoản từ Starter / Free lên Google AI Pro:
1. Cần cập nhật `providerSpecificData` trong connection qua `PUT /api/providers/<id>`:
   ```python
   psd = conn.get("providerSpecificData") or {}
   psd["tier"] = "g1-pro-tier"
   psd["subscriptionTier"] = "Antigravity Pro"
   psd["plan"] = "Antigravity Pro"
   omni_put(f"/api/providers/{conn['id']}", {"providerSpecificData": psd, "isActive": True})
   ```
2. Đưa connection ID vào combo `ag-gemini-pool-3` nếu combo chưa chứa ID này để router tự động phân phối tải.

---

## 3. VM Guest File Automation Quirks (Windows ReadOnly Attributes)

### Vấn đề:
Khi chạy quy trình giải cứu Antigravity Pro qua VM (`vm_rescue_lib.py`), lệnh `vmrun copyFileFromHostToGuest` hoặc `deleteFileInGuest` đưa file config vào `C:\ag-kit\sing-box\` bị trả mã lỗi `4294967295` (-1 / exit code 127):
`Error: You do not have access rights to this file`.

### Nguyên nhân:
Các file template giải nén sẵn trong snapshot `baseline-v2.17` của Windows Guest mang thuộc tính `ReadOnly, Archive`. API `copyFileFromHostToGuest` của VMware Tools không thể ghi đè trực tiếp lên file có cờ `ReadOnly`.

### Giải pháp chuẩn:
Xóa cưỡng chế bằng PowerShell guest trước khi copy file mới:
```powershell
if (Test-Path -LiteralPath '$guest_path') { Remove-Item -LiteralPath '$guest_path' -Force }
```
Sau đó mới gọi `copyFileFromHostToGuest`.
