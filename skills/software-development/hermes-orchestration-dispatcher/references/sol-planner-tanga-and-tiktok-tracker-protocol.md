# Sol Planner Tầng A & TikTok Farm Tracker Protocol (2026-09-17)

## 1. Bối cảnh & Quy tắc bắt buộc
- **User Invariant (2026-09-17)**: *"Ủa sao k gọi sol lên plan nhỉ mà m lên plan?"*
- Coordinator CẤM TUYỆT ĐỐI tự ý lên plan một mình rồi dispatch worker. Mọi task phát triển tính năng / tool mới BẮT BUỘC phải qua **Sol Web (:20129)** lập plan Tầng A.

## 2. Quy trình 4 bước chuẩn
```text
1. SOL PLANNER (Tầng A Offline):
   python D:/Taadaa/tools/sol_planner.py --goal "<Mục tiêu>" --file "<Target file>"
   -> Nhận sol_plan_id, diagnosis, strategy và danh sách tasks T1..Tn.

2. DISPATCH WORKER (Tầng B):
   - Contract khép kín, budget <= 15 calls.
   - Unit Test BẮT BUỘC MOCK 100%: cấm gọi HTTP/network thật trong pytest suite.
   - Pytest bắt buộc chạy hoàn tất < 10 giây.

3. BOUNDED LIVE VERIFY:
   - Chỉ chạy live request khi pytest đã PASS hoàn toàn.
   - Khống chế tham số an toàn (ví dụ: --limit 2..3).

4. SOL AUDITOR (Chốt phiên Scorecard):
   python D:/Taadaa/tools/sol_auditor.py
   -> Sol Web chấm điểm Scorecard (yêu cầu >= 85 điểm mới được đóng phiên).
```

## 3. TikTok Web Scraping Bypass WAF (Mobile Safari)
- **Vấn đề**: TikTok desktop web chặn bot/script bằng SlardarWAF (`<script id="slardar-config">`), trả về trang 1.4KB không có dữ liệu tài khoản.
- **Giải pháp**: BẮT BUỘC dùng Mobile User-Agent (Safari iOS):
  ```python
  headers = {
      'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
      'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
      'Accept-Language': 'vi-VN,vi;q=0.9,en-US;q=0.8',
  }
  ```
- **Dữ liệu trích xuất**: Thẻ `<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__">` chứa JSON đầy đủ:
  - `data['__DEFAULT_SCOPE__']['webapp.user-detail']['userInfo']['user']`: UID, uniqueId, nickname, secUid.
  - `data['__DEFAULT_SCOPE__']['webapp.user-detail']['userInfo']['stats']`: followerCount, followingCount, heartCount, videoCount.
  - Nick không tồn tại / die: `statusCode == 10221` hoặc `userInfo is None`.
