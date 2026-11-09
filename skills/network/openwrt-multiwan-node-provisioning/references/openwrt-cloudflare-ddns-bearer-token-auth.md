# OpenWrt Headless Cloudflare DDNS: Global API Key Auth Failure (Error 10000) vs Scoped Bearer Token

## 1. Hiện tượng lỗi (The Incident)
Khi cài đặt script cập nhật DDNS Cloudflare (`cf_ddns.sh`) chạy tự động qua cron trên OpenWrt router (Xiaomi R3G):
- Gọi API cập nhật bản ghi DNS bằng Header Global API Key:
  ```sh
  curl -s -X PUT "https://api.cloudflare.com/client/v4/zones/{ZONE_ID}/dns_records/{RECORD_ID}" \
      -H "X-Auth-Email: user@example.com" \
      -H "X-Auth-Key: <global_key>" \
      -H "Content-Type: application/json" \
      --data "$PAYLOAD"
  ```
- Kết quả phản hồi từ Cloudflare API:
  ```json
  {
    "success": false,
    "errors": [
      {
        "code": 10000,
        "message": "Authentication error",
        "documentation_url": "https://developers.cloudflare.com/api/resources/dns/subresources/records/methods/update"
      }
    ]
  }
  ```
- **Hậu quả:** File cache `/tmp/last_cf_ip` không được ghi, bản ghi DNS `tb.taadaa.click` không được cập nhật khi IP WAN thay đổi, router bị mất kết nối từ xa.

## 2. Nguyên nhân gốc rễ (Root Cause)
1. **Lệch chuẩn Auth Header:**
   - Nhiều tài khoản Cloudflare hiện đại tắt hoặc siết quyền Global API Key đối với các endpoint ghi đè DNS trực tiếp qua HTTP REST, hoặc key cấu hình trong các tool bên thứ ba (như MobiProxy) là token có format đặc thù (`cfk_...`) không tương thích với header `X-Auth-Key` truyền thống.
2. **Thiếu tính tương thích với Scoped API Token (Bearer Token):**
   - Cloudflare API chuẩn hiện nay yêu cầu xác thực bằng **API Token có quyền Edit DNS (Zone.DNS Edit)** qua Header:
     ```http
     Authorization: Bearer <API_TOKEN>
     ```
   - Khi chuyển sang dùng API Bearer Token chính chủ (`cfut_...`), request được xác thực ngay lập tức và trả về `"success": true`.

## 3. Bản mẫu chuẩn (Production DDNS Script cho OpenWrt Router)
File `/root/cf_ddns.sh`:
```sh
#!/bin/sh
# Cloudflare DDNS Updater for OpenWrt Headless Router
WAN_IP=$(ip -4 addr show dev pppoe-wan_sub11 2>/dev/null | grep -oE 'inet [0-9.]+' | cut -d' ' -f2)
[ -z "$WAN_IP" ] && WAN_IP=$(ip -4 addr show dev pppoe-wan 2>/dev/null | grep -oE 'inet [0-9.]+' | cut -d' ' -f2)

if [ -z "$WAN_IP" ]; then
    exit 1
fi

CACHE_IP=$(cat /tmp/last_cf_ip 2>/dev/null)
if [ "$WAN_IP" = "$CACHE_IP" ]; then
    exit 0
fi

ZONE_ID="7ec2923fdd73bba508b64cb69e013d71"
RECORD_ID="d0e637c645a10208df5b909a6404b86e"
RECORD_NAME="tb.taadaa.click"
CF_TOKEN="cfut_EXAMPLE_DUMMY_TOKEN_REPLACED"

URL="https://api.cloudflare.com/client/v4/zones/${ZONE_ID}/dns_records/${RECORD_ID}"
PAYLOAD="{\"type\":\"A\",\"name\":\"${RECORD_NAME}\",\"content\":\"${WAN_IP}\",\"ttl\":60,\"proxied\":false}"

RES=$(curl -s -X PUT "$URL" \
    -H "Authorization: Bearer ${CF_TOKEN}" \
    -H "Content-Type: application/json" \
    --data "$PAYLOAD")

echo "$RES" | grep -q '"success":true' && echo "$WAN_IP" > /tmp/last_cf_ip
```

## 4. Kích hoạt Crontab & Kiểm tra Telemetry
1. Cấp quyền thực thi:
   ```sh
   chmod +x /root/cf_ddns.sh
   ```
2. Thêm vào `/etc/crontabs/root`:
   ```sh
   */2 * * * * /bin/sh /root/cf_ddns.sh >/dev/null 2>&1
   ```
3. Restart cron service:
   ```sh
   /etc/init.d/cron enable
   /etc/init.d/cron restart
   ```
4. Kiểm chứng:
   - File `/tmp/last_cf_ip` chứa đúng IP WAN hiện tại.
   - Phân giải DNS từ Google (`8.8.8.8`): `https://dns.google/resolve?name=tb.taadaa.click&type=A` trả về đúng IP vừa cập nhật.
