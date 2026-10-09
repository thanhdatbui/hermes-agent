# TikTok Web Profile Scraping: SlardarWAF Handling & Proxy Pool Rotation

## Context
When scraping or tracking TikTok account status (LIVE, NOT_FOUND/DIE, RATE_LIMITED) via TikTok web profile endpoints (`https://www.tiktok.com/@<username>`):
- Profile data is typically embedded in `<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__" ...>{...}</script>`.
- Under heavy scraping or when TikTok triggers anti-bot/WAF defenses, the response does not return hydration data, but returns a challenge page involving `SlardarWAF` (or `slardar`).
- Treating absence of hydration data blindly as `NOT_FOUND` or `DIE` causes false-positive account dead alerts across the farm.

## Detection Rules
1. **Hydration Script Found**:
   - `statusCode == 10221`: Genuine `NOT_FOUND` (nick die/không tồn tại).
   - `statusCode == 0` with valid `userInfo`: `LIVE`.
2. **No Hydration Script Found**:
   - Check if response HTML contains `SlardarWAF` or `slardar` (case-insensitive).
   - If present: classify status as `RATE_LIMITED` (WAF blocked, nick is likely alive but request got challenged).
   - If absent: classify as `ERROR` (corrupted response or unexpected page layout).

## Proxy Pool & Rotation Strategy
- Taadaa Farm local proxy pool: 32 ports ranging from `20001` to `20032` on `192.168.110.2`:
  ```python
  PROXY_POOL = [
      f'http://TaadaaMobi%232026%21:TaadaaMobi%232026%21@192.168.110.2:{port}'
      for port in range(20001, 20033)
  ]
  ```
- **Retry Pattern**:
  - Rotate proxy randomly on each attempt.
  - When encountering `RATE_LIMITED` or connection/timeout exceptions, retry up to 2 times with a different proxy before recording an error.
