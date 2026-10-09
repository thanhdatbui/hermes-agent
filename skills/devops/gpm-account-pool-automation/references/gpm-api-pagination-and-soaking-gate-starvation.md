# GPMLogin Local API Pagination & Soaking Gate Starvation

## 1. Hiện tượng & Vấn đề thực tế (Silent Pagination Blindness)
Khi số lượng profile trong GPMLogin tăng lên (ví dụ: toàn farm có 599 profiles trên GPM v3):
- Endpoint `GET /api/v3/profiles` trả về cấu trúc phân trang:
  ```json
  {
    "success": true,
    "data": [...],
    "pagination": { "total": 599, "page": 1, "page_size": 300, "total_page": 2 }
  }
  ```
- **Lỗi kinh điển**: Các script tự động hoá gọi hardcoded `page=1&per_page=300`.
- Hậu quả: Toàn bộ 299 profile ở trang 2 (vị trí 301 đến 599) bị "mù" hoàn toàn đối với script.

## 2. Hiệu ứng dây chuyền với Soaking Gate (2FA Starvation)
- Script nuôi định kỳ (`cron_gpm_gmail_nurture.py`) chỉ quét trang 1 $\rightarrow$ các profile trang 2 không bao giờ được chọn để nuôi.
- File state `gpm_gmail_nurture_state.json` không bao giờ ghi nhận `last_nurtured` cho các profile này.
- Watchdog bật 2FA (`post_morning_gmail_2fa_watchdog.py`) áp dụng **Soaking Gate** nghiêm ngặt (bắt buộc acc phải được nuôi thành công ít nhất 1 phiên trên GPM để tránh Google checkpoint).
- Do thiếu `last_nurtured`, Soaking Gate liên tục chặn kích hoạt 2FA.
- Báo cáo định kỳ 6h (`cron_gmail_gpm_2fa_6h_report.py`) bị kẹt cứng (ví dụ: 73/76 profile, 3 acc kẹt "Đang ngâm", 0 acc sẵn sàng) suốt nhiều ngày dù các acc vẫn sống.

## 3. Quy chuẩn lập trình GPM API (Invariant Pagination Pattern)
BẮT BUỘC duyệt toàn bộ phân trang hoặc lọc theo `group_id` cụ thể khi tương tác với GPM Local API:

```python
def get_all_gpm_profiles(base_url="http://127.0.0.1:19995/api/v3", group_id=None, per_page=300) -> list:
    """Lấy trọn vẹn danh sách profile qua vòng lặp phân trang an toàn."""
    all_profiles = []
    page = 1
    while True:
        try:
            params = f"page={page}&per_page={per_page}"
            if group_id is not None:
                params += f"&group_id={group_id}"
            url = f"{base_url}/profiles?{params}"
            
            res = requests.get(url, timeout=15).json()
            data = res.get("data")
            items = data if isinstance(data, list) else (data or {}).get("list", [])
            if not items:
                break
            all_profiles.extend(items)
            
            pag = res.get("pagination") or {}
            if page >= pag.get("total_page", 1):
                break
            page += 1
        except Exception as e:
            logger.error(f"Lỗi kết nối GPM API (page {page}): {e}")
            break
    return all_profiles
```

## 4. Kiểm tra Auth Session Google trực tiếp qua SQLite Cookie
Trước khi đưa profile vào luồng nuôi hoặc bật 2FA, có thể kiểm chứng session offline nhanh < 1s mà không cần khởi động trình duyệt:

- **Đường dẫn**: `<ProfilePath>/Default/Network/Cookies` (Chromium hiện đại) hoặc `<ProfilePath>/Default/Cookies`.
- **Query**:
  ```sql
  SELECT name FROM cookies 
  WHERE host_key LIKE '%google.com' 
    AND name IN ('SID', 'SSID', 'HSID', 'SAPISID');
  ```
- **Đánh giá**:
  - Đủ cả 4 cookie $\rightarrow$ Session Google LIVE hoàn toàn, sẵn sàng nuôi / bật 2FA.
  - 0 cookie auth (chỉ có cookie tracking) $\rightarrow$ Session Google đã hết hạn / bị out login, cần đưa vào watchdog re-login trước khi nuôi.
