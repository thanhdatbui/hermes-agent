# OmniRoute ModelLockout Cooldown Tuning & Free-Pool Cascade Prevention (2026-10-04)

## Bối cảnh sự cố
1. Bot Hermes gửi liên tiếp payload context lớn (400–700 messages, 260k+ tokens).
2. Khi proxy chập chờn (ví dụ các port 5113, 5115, 5135 trên VPS proxy trả 503), OmniRoute kích hoạt cơ chế `modelLockout`.
3. Bẫy cấu hình cũ: `modelLockout.baseCooldownMs` bị đặt ở mức **600.000ms (10 phút)** và trần `maxCooldownMs = 1.800.000ms (30 phút)`.
4. Hậu quả: Chỉ sau vài lỗi proxy thoáng qua, toàn bộ 20 tài khoản Pro bị giam trong cooldown 10 phút. Hàng loạt request báo:
   `antigravity | hard-bound connection <id> unavailable; refusing sibling selection`
5. Cascade Trap: Khi Tier 1 (Pro) cạn slot, combo router tràn tải sang Tier 2 (`ag-gemini-free-pool` gồm 79 tài khoản Free). Việc duyệt tuần tự và clone request 600+ messages qua 79 accounts trong RAM làm Node.js V8 heap vượt trần gây OOM crash.

## Chuẩn hóa cấu hình (Đã áp dụng live & Sol duyệt)
Trong `C:/Users/Kibe/.omniroute/storage.sqlite` và `settings_backup.json`:

```json
"modelLockout": {
  "enabled": true,
  "errorCodes": [403, 404, 429, 502, 503, 504],
  "baseCooldownMs": 120000,
  "maxCooldownMs": 600000,
  "maxBackoffSteps": 5,
  "useExponentialBackoff": true
}
```

### Các nguyên tắc bất biến:
1. **Cooldown 120s:** Khi proxy hoặc upstream chập chờn, tài khoản Pro hồi sinh sau 2 phút (thay vì 10 phút), tránh cạn kiệt slot đồng loạt.
2. **Trần lùi bước 5 (Max 10 phút):** Giới hạn tối đa không vượt quá 600.000ms dù dính liên tiếp nhiều lỗi.
3. **Phòng chống OOM khi cascade:** Không cho phép request nặng context (>100k tokens / >200 msgs) cascade tràn lan qua toàn bộ 79 accounts Free. Cần fail-fast 429 để client retry thay vì clone bộ nhớ duyệt 79 lần.
