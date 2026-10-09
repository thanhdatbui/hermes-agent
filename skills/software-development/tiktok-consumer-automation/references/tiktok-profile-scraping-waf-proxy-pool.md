# TikTok Profile Web Scraping: SlardarWAF Detection & MobiProxy Pool

## 1. Nguyên nhân False DIE / NOT_FOUND
Khi cào dữ liệu profile TikTok qua endpoint web (`https://www.tiktok.com/@username`):
- TikTok thường xuyên chặn IP/bot bằng trang challenge WAF chứa chuỗi `SlardarWAF`.
- Trong trang WAF, thẻ `<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__">` hoàn toàn không tồn tại.
- Nếu parser chỉ kiểm tra sự tồn tại của script tag này và fallback về `NOT_FOUND`, hàng loạt tài khoản sống (LIVE) sẽ bị đánh đồng thành `NOT_FOUND` / `DIE` oan uổng.

## 2. Quy tắc phân loại trạng thái chuẩn
- **LIVE**: Trích xuất được `userInfo` và `statusCode == 0` (hoặc khác 10221).
- **NOT_FOUND (Thực sự)**: Trích xuất được JSON hydration với `statusCode == 10221` hoặc response trả về HTTP `404`.
- **BLOCKED / WAF**: HTML chứa `SlardarWAF` mà không có dữ liệu hydration JSON. Trạng thái này là lỗi do IP/anti-bot, **tuyệt đối không được gán `NOT_FOUND` hoặc `DIE`**.
- **ERROR**: Các ngoại lệ mạng, DNS, timeout khi kết nối.

## 3. Cấu hình MobiProxy Pool (32 Ports)
Sử dụng pool 32 cổng proxy xoay vòng trên gateway nội bộ farm:
```python
PROXY_POOL = [
    f'http://TaadaaMobi%232026%21:TaadaaMobi%232026%21@192.168.110.2:{port}'
    for port in range(20001, 20033)
]
```

## 4. Cơ chế Retry thông minh (Smart Retry)
- Khi fetch gặp `SlardarWAF` hoặc `Timeout`/`ConnectionError`:
  1. Loại trừ các proxy đã thử trong phiên request này.
  2. Chọn ngẫu nhiên proxy khác từ pool chưa thử.
  3. Thực hiện retry tối đa 2 lần (tổng cộng 3 attempts).
- Nếu sau 2 lượt retry vẫn bị chặn hoặc timeout:
  - Trả về kết quả với `status: 'BLOCKED'` hoặc `status: 'ERROR'`.
  - Phân loại trong báo cáo summary và database tách biệt hoàn toàn khỏi nhóm `DIE/NOT_FOUND`.

## 5. CLI Flags & Tuân thủ
- Cung cấp cờ `--use-proxy` (mặc định True với `argparse.BooleanOptionalAction`) và alias `--no-proxy`.
- Lưu snapshot vào SQLite `D:/Taadaa/data/tiktok_tracker.db` với cột `status` phản ánh chính xác (`LIVE`, `NOT_FOUND`, `BLOCKED`, `ERROR`).
