# TikTok Farm Stats Tracking & Public Web Extraction Protocol (2026-09-17)

## 1. Bối cảnh & Yêu cầu
- Theo dõi toàn bộ ~590 tài khoản TikTok của Farm: thống kê Follower, Following, Heart/Like, Số Video, trạng thái LIVE/DIE và tự động phát hiện tài khoản cắn đề xuất.
- **Tiêu chí tối cao**: Không dùng dịch vụ SaaS bên ngoài (tốn kém, nguy cơ lộ dàn), không đụng chạm máy S7 hay chiếm dụng tài nguyên farm (không dùng ADB hay app TikTok trên máy).

## 2. Kỹ thuật Bypass WAF (Mobile Safari Hydration JSON)
- Endpoint: `https://www.tiktok.com/@{username}`
- Trình duyệt Desktop bị chặn bởi SlardarWAF (`<script id="slardar-config">`), trả về HTML 1.4KB không có dữ liệu tài khoản.
- BẮT BUỘC dùng Mobile User-Agent của iPhone Safari:
  ```python
  headers = {
      'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
      'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
      'Accept-Language': 'vi-VN,vi;q=0.9,en-US;q=0.8',
  }
  ```
- Dữ liệu trả về nằm trong thẻ script:
  `<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__" type="application/json">`
- Các trường trích xuất chính:
  - `data['__DEFAULT_SCOPE__']['webapp.user-detail']['userInfo']['user']`: `id` (UID gốc), `uniqueId`, `nickname`, `secUid`.
  - `data['__DEFAULT_SCOPE__']['webapp.user-detail']['userInfo']['stats']`: `followerCount`, `followingCount`, `heartCount`, `videoCount`, `friendCount`.
  - Nhận diện DIE / Banned: `statusCode == 10221` hoặc `userInfo is None`.

## 3. Hệ thống Lưu trữ & Phát hiện Cắn Đề Xuất
- SQLite Database: `D:/Taadaa/data/tiktok_tracker.db` lưu snapshot theo mốc thời gian.
- Tính toán Delta:
  - $\Delta \text{Follower} = \text{Follower}_{\text{hôm nay}} - \text{Follower}_{\text{hôm trước}}$
  - $\Delta \text{Like} = \text{Like}_{\text{hôm nay}} - \text{Like}_{\text{hôm trước}}$
  - Đánh dấu `🔥 CẮN ĐỀ XUẤT` khi $\Delta \text{Follower} \ge 10$ hoặc $\Delta \text{Like} \ge 50$.
- Báo cáo Excel: `D:/OneDrive/TaadaaData/kibe/tiktok_stats_farm.xlsx` (tự động đồng bộ lên OneDrive để xem trên di động/máy tính).

## 4. Tự động hóa qua Hermes Cron (07:00 Hàng Ngày)
- Job ID: `daily-tiktok-farm-tracker` (`0 7 * * *`, `no_agent=True`).
- Script wrapper: `cron_tiktok_daily_tracker.py` tuân thủ quy tắc đồng bộ 3 nơi:
  1. `C:/Users/Kibe/AppData/Local/hermes/scripts/cron_tiktok_daily_tracker.py`
  2. `D:/Taadaa/Hermes/deploy/hermes-home/scripts/cron_tiktok_daily_tracker.py`
  3. `D:/OneDrive/Taadaa_Sync_Shared/hermes-cron/scripts/cron_tiktok_daily_tracker.py`
- Tự động in bảng tóm tắt gửi về Telegram sau khi quét xong 10 workers song song (~1-2 phút).
