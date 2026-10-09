# TikTok Feed Session Test on Real S7 Devices (11/09/2026)

## Test Context
- **Environment**: 79 Samsung S7 online via ADB, proxy qua MobiProxy (MikroTik Sing-box → Box Thái Bình)
- **Test Scope**: Máy `device:2b8f467465` (Máy 1, proxy cổng 20001 → MobiProxy 5101, IP egress: 116.107.115.121)
- **Account**: `lipsellczaw` (Row 1, Sheet `Accounts`, `taikhoan_run_safe.xlsx`)

## Flow Verification Results

| Bước | Kết quả | Ghi chú |
|:---|:---:|:---|
| Wake/Unlock | ✅ | Màn hình bật, bỏ khóa |
| Force stop & Launch TikTok | ✅ | App khởi động sạch |
| Verify TikTok focus | ✅ | Thử lại 1 lần (lần 1 bị systemui) → OK |
| Baseline screen classify (For You) | ✅ | Confidence 0.9, XML/screenshot match |
| Profile identity guard | ✅ | Màn Profile đúng user |
| Switch account anchor tap | ✅ | Tap đúng element |
| Account switcher sheet | ⚠️ | Phát hiện "Add phone" (manual-needed) — **bình thường acc mới** |
| Tap expected account | ✅ | Tap đúng `lipsellczaw` |
| Nav tab Profile | ✅ | Chuyển tab thành công |

## Proxy Performance (MobiProxy 32 cổng)
- 32/32 cổng (5101–5138): **THÔNG 100%**, latency ~0.45s/request
- Web admin: HTTP 200 load ~1s, **không 502**
- 79 máy S7 online: TikTok feed session chạy OK

## Key Takeaways
1. **Máy `ce031603...` (cổng 10002)** bị lỗi do trỏ sai cụm proxy (dải 100xx) — cần đồng bộ lại proxy mapping trong `PROXYgandienthoai.xlsx`.
2. **MobiProxy Scan Guard** (firmware 3.0.67+) hoạt động ổn: firewall iptables kernel, update whitelist IP không restart proxy.
3. Hệ thống **sẵn sàng cho cron `phase9-runner-tiktok-feed`** (15 phút/lần) từ ngay lúc này.