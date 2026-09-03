# TikTok Checklive trực tiếp từ VPS Doravo (2026-08-20, verified)

## Vì sao GH Actions thất bại (bài học)
- GitHub Actions runner (IP datacenter Ubuntu) bị TikTok WAF chặn phần lớn profile request:
  chạy 487 acc → **LIVE 8 / DIE 102 / UNKNOWN 377 (77%)** — UNKNOWN không phải acc die,
  là WAF block. Không được xoá UNKNOWN khỏi kho.
- Playwright headless/headful từ IP nhà (C:\Users\Kibe) CŨNG bị chặn: profile page trả HTML
  dài ~100-130KB nhưng KHÔNG có `<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__">`.
- VPS Doravo (`152.42.187.200`, SGP DigitalOcean) với urllib + đủ header + retry = kênh duy nhất hoạt động.

## Cơ chế phân loại (chính xác, đã test 5/5 mẫu)
- GET `https://www.tiktok.com/@{user}?lang=en` với header:
  - `User-Agent`: Chrome 125 full string
  - `Accept`: `text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8`
  - `Accept-Language: en-US,en;q=0.9`
  - `Accept-Encoding: identity` (tránh gzip làm hỏng vị trí tag)
  - `Sec-Fetch-Dest: document`, `Sec-Fetch-Mode: navigate`, `Sec-Fetch-Site: none`
  - `Upgrade-Insecure-Requests: 1`, `Connection: keep-alive`
- Parse: tìm `__UNIVERSAL_DATA_FOR_REHYDRATION__` → cắt từ `>` tới `</script>` → JSON
  → `__DEFAULT_SCOPE__.webapp.user-detail`:
  - `statusCode == 0` + có `userInfo` → **LIVE**
  - `statusCode == 10221` → **DIE** (banned / không tồn tại)
  - thiếu tag (HTML ngắn ~12-1.4KB = WAF challenge) → **UNKNOWN → retry**
- **Retry tối đa 4 lần, sleep 0.8s giữa lần** — WAF block ngẫu nhiên 30-50% request/lần, retry đẩy độ phủ lên ~95-100%.
- Batch 20 acc/command (tránh argv dài), mỗi lệnh chạy qua:
  `ssh -i ~/.ssh/doravo_deploy root@152.42.187.200 "python3 -c '<script>' '<user1,user2,...>' 4"`
- Kết quả thực tế: `tiktok→LIVE`, `khaby.lame→LIVE`, `sonaairhrk395682→DIE`, `oxyzldz362255914→DIE`, `fake→DIE`.

## GH Actions fallback (khi cần chạy cloud)
- Workflow: `thanhdatbui/tiktok_check_live` workflow `tiktok-checklive.yml`, dispatch qua
  `POST /actions/workflows/tiktok-checklive.yml/dispatches` với `inputs.request_id` + `inputs.payload_b64`.
- **Poll timeout 60 phút** (487 acc mất ~35 phút — script 10 phút bỏ sót run).
- **Artifact download 401 fix**: GH trả 302 redirect tới host khác; urllib mặc định giữ header
  `Authorization` → 401 `Server failed to authenticate`. Fix:
  ```python
  class NoAuthRedirect(urllib.request.HTTPRedirectHandler):
      def redirect_request(self, req, fp, code, msg, headers, newurl):
          newreq = super().redirect_request(req, fp, code, msg, headers, newurl)
          if newreq is not None:
              newreq.headers = {k: v for k, v in req.headers.items()
                                if k.lower() not in ("authorization",)}
          return newreq
  opener = urllib.request.build_opener(NoAuthRedirect)
  ```
  Dùng `opener` cho cả 2 request: list artifacts + download zip.
- Run ID lấy từ `GET /actions/runs?per_page=10` match `display_title == request_id`.
- Artifact zip chứa `checklive-result.json` (`results: [{username, status}]`).

## Lưu ý vận hành kho
- Chỉ xoá DIE; UNKNOWN giữ nguyên.
- Di chuyển DIE: INSERT vào `product_die` (product_code, seller, uid, account, create_gettime, type) rồi DELETE khỏi `product_stock` theo chunk 200 trong transaction.
- Backup trước khi dọn: TSV dump `product_stock WHERE id IN (...)` vào `/var/www/shopclone7/backups/pre-tt-clean-die/<ts>/`.
- Cron script chuẩn: `~/AppData/Local/hermes/scripts/daily_manual_stock_checklive.py` (job `daily-manual-stock-checklive`, 03:00 hằng ngày) — hàm `check_tiktok_batch()` chính là recipe này.
