# Proxy Egress Death → Global Provider Cooldown Cascade

## Incident Pattern (Observed 2026-10-07 ~04:50 VN / 21:41 UTC)

### Symptom
Client sees 503 hàng loạt trên nhiều sessions trong thời gian ngắn. OmniRoute log ghi:
```
Skipping antigravity/gemini-3.8-flash-tiered — provider antigravity in global cooldown
```
Kèm theo trước đó:
```
[Proxy Fast-Fail] Proxy unreachable: http://test.taadaa.click:5121
[Proxy Fast-Fail] Proxy unreachable: http://test.taadaa.click:5115
[Proxy Fast-Fail] Proxy unreachable: http://test.taadaa.click:5107
[Proxy Fast-Fail] Proxy unreachable: http://test.taadaa.click:5101
```

### Root Cause Chain
1. Nhiều proxy egress port chết đồng thời (test.taadaa.click:5101, :5107, :5115, :5121)
2. Acc Antigravity được gán các proxy đó phản hồi 503 fast-fail ngay lập tức
3. OmniRoute ghi `Model-only lockout` failureCount=1 (5s), failureCount=2 (10s) khi cùng 1 proxy fail 2 lần liên tiếp
4. Sau 2 lần fail, OmniRoute trip **Global Provider Cooldown** cho toàn bộ `provider: antigravity`
5. **Tất cả** acc Gemini trong pool đều bị skip — kể cả acc còn sống bình thường không liên quan proxy chết
6. Client thấy 503 stream trên mọi session dùng omni-worker

### Phân biệt với các 503 khác

| Loại | Dấu hiệu trong log | Nguyên nhân |
|---|---|---|
| **Proxy-cascade (bài này)** | `[Proxy Fast-Fail] Proxy unreachable` → `global cooldown` | Proxy egress chết hàng loạt |
| **Semaphore timeout** | `Semaphore timeout after 30000ms` → `429` | Acc gánh quá nhiều request nặng |
| **TPM/RPM stampede** | `429 RESOURCE_EXHAUSTED` → spillover nhiều acc → `ALL_TARGETS_SKIPPED` | Quá nhiều session song song |
| **Weekly quota cạn** | `Individual quota reached. Resets in 101h46m` | Free tier acc hết hạn mức tuần |

### Recovery
- **Tự recover:** Khi proxy egress sống lại, global cooldown hết hạn, pool tự phục hồi
- **Manual reset nếu cooldown kéo dài:** `curl -X DELETE http://localhost:20129/api/monitoring/health`
- **Fallback:** Trong thời gian cooldown, combo fallback xuống `chatgpt-web/gpt-5.6-sol-high` vẫn serve được

### Pitfalls
- **ĐỪNG nhầm với 429 quota:** Proxy-cascade tạo `503` logs ở COMBO tag, không phải TELEMETRY 429 từ Google
- **Acc dính 403 "Verify your account":** Riêng biệt, không liên quan cascade. Là acc cần re-auth Google, không phải proxy lỗi
- **429 upstream thật sau recovery:** Sau khi cooldown hết, nếu thấy `quotaResetDelay: 101h46m` đó là weekly quota cạn (2 acc riêng biệt bị cạn trong incident này) — không phải cascade tiếp tục

### Ngăn Tái Phát (Chưa được cấu hình)
- Hiện tại ngưỡng global cooldown quá nhạy: chỉ cần 2 lần proxy fail 503 = cấm cả pool
- Đề xuất: tách `cooldown per-connection` thay vì `global provider cooldown` khi nguyên nhân là proxy egress
- Hoặc tăng `MaxConsecutiveFailures` trước khi trip global cooldown lên ít nhất 4-5 lần

### Chẩn đoán nhanh khi nhận báo cáo 503
```bash
# 1. Xác nhận proxy egress là nguồn gốc
grep "Proxy Fast-Fail\|Proxy unreachable" omniroute-stdout.log | tail -20

# 2. Xác nhận global cooldown cascade theo sau
grep "provider antigravity in global cooldown" omniroute-stdout.log | tail -10

# 3. Xem thời điểm bắt đầu cascade
grep "global cooldown\|Proxy unreachable" omniroute-stdout.log | head -20

# 4. Kiểm tra ngay trạng thái hiện tại pool
curl -s http://localhost:20129/api/monitoring/health | jq '.providers.antigravity'
```
