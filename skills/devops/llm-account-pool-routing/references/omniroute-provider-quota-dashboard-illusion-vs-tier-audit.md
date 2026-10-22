# OmniRoute Provider Quota Dashboard Illusion vs Tier Breakdown

## 1. Triệu Chứng & Hoang Mang Thường Gặp
Người vận hành nhìn vào giao diện **Provider Quota** (`http://<ip>:20129/dashboard/quota`) và thấy một loạt thẻ Antigravity hiển thị:
- Chấm đỏ hoặc nhãn **`Token expired`**
- Nút gạt Toggle chuyển sang màu xám (**OFF / Inactive**)
- Quota các model Claude/Gemini cạn kiệt (0% left)

Dẫn tới câu hỏi/hoang mang: *"Con nào đi tắt hết đống acc Google Pro của tôi?"* hoặc nghi ngờ có script watchdog chạy ẩu làm hỏng/tắt pool tài khoản.

---

## 2. Nguyên Nhân Kỹ Thuật (Dashboard Quota Illusion)

1. **Hiển thị hỗn tạp không phân tầng (All-Tier Flat View)**:
   - Trang `/dashboard/quota` của OmniRoute liệt kê **toàn bộ 100+ connection** thuộc provider `antigravity` trên cùng một mặt phẳng, KHÔNG phân tách theo tier (`g1-pro-tier` vs `standard-tier` vs `free-tier`).
   - Các tài khoản hiển thị `Token expired` hoặc Toggle OFF thực chất là:
     * **`standard-tier` Inactive**: ~20–30 tài khoản Google thường/doanh nghiệp được chủ động tắt (`is_active = 0`) để làm tài khoản dự phòng hoặc nuôi dưỡng, không tham gia pool chính.
     * **`free-tier` Expired**: Các tài khoản miễn phí từ farm/reg cũ đã bị Google thu hồi token (`unrecoverable_refresh_error` / HTTP 401).
   - **Dàn Google AI Pro (`g1-pro-tier`)** phục vụ tác vụ chính (Hermes Coordinator/Worker, AGY CLI) vẫn **100% ACTIVE (`isActive: true`, `testStatus: active`)** và token luôn được tự động làm mới (`expiresIn: ~3599s`).

2. **Dữ liệu hiển thị Stale Cache / Quota Snapshot cũ**:
   - Các thẻ trên Quota Dashboard ghi nhận thời gian `Updated HH:MM:SS` từ lần cuối giao diện hoặc job đo quota truy vấn.
   - Nếu giao diện mở qua nhiều giờ, các thẻ chưa được trigger request sẽ giữ nguyên nhãn cũ (ví dụ `Updated 09:33:04` lúc 11:28 AM), tạo cảm giác token bị chết hàng loạt dù thực tế upstream token đã được xoay vòng tự động.

---

## 3. Quy Trình Đối Soát O(1) Tức Thì (Diagnostic Workflow)

Khi nhận phản ánh về việc acc Google/Antigravity bị tắt hoặc expired:

### Bước 1: Truy vấn phân loại trực tiếp qua API `:20129/api/providers` (hoặc SQLite `~/.omniroute/storage.sqlite`)

```python
import urllib.request, json

data = json.loads(urllib.request.urlopen('http://127.0.0.1:20129/api/providers', timeout=10).read().decode())
conns = [c for c in data.get('connections', []) if c.get('provider') == 'antigravity']

# 1. Tách riêng dàn Pro
pro_conns = [c for c in conns if (c.get('providerSpecificData') or {}).get('tier') == 'g1-pro-tier']
pro_active = [c for c in pro_conns if c.get('isActive') and c.get('testStatus') == 'active']

# 2. Tách các nhóm Inactive / Expired
inactive = [c for c in conns if not c.get('isActive')]
expired = [c for c in conns if c.get('testStatus') == 'expired']

print(f"Tổng Antigravity: {len(conns)}")
print(f"Pool Pro: {len(pro_active)}/{len(pro_conns)} LIVE (100% active nếu không có sự cố)")
print(f"Inactive (tắt chủ động): {len(inactive)} (đa phần standard-tier)")
print(f"Expired (token revoked): {len(expired)} (đa phần free-tier cũ)")
```

### Bước 2: Báo cáo minh bạch & trấn an với số liệu cứng
- Khẳng định ngay dàn **Pool Pro (`g1-pro-tier`)** còn nguyên vẹn bao nhiêu tài khoản (ví dụ 26/26 LIVE).
- Chỉ rõ các tài khoản đang đỏ thực chất thuộc `standard-tier` (đang tạm tắt có chủ đích) hoặc `free-tier` (token chết từ trước), không ảnh hưởng đến năng lực tính toán và routing của hệ thống.
