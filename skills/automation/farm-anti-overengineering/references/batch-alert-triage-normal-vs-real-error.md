# Batch Alert Triage — "Normal Skip" vs "Real Error" Pattern

## Nguyên tắc cốt lõi

Khi nhận batch alert có nhiều signature lỗi, BẮT BUỘC phân loại trước khi hành động:
1. Một số signature có thể là **thiết kế bình thường** (expected skip) — không phải bug
2. Chỉ xử lý signature là **lỗi thực** (unexpected failure)

Phân loại sai → alert giả → tốn thời gian điều tra hoặc fix sai chỗ.

## Case Study: Ca nuôi Row 7/8 (2026-09-09)

**Batch alert nhận được:** 80 máy, thành công 2, thất bại 78

**Signature 1 (75%, 60 máy):** `account row 7 is empty (no username) for <device>, skipping`
- **Phân tích:** Row 7 = Slot 7 (Incubator slot). Hầu hết máy chưa reg xong nick Slot 7 → workbook trống → runner skip theo thiết kế `eight-slot-incubator`.
- **Kết luận: BÌNH THƯỜNG.** Không cần can thiệp.

**Signature 2 (18.8%, 15 máy):** `profile username still mismatched after switch`
- **Phân tích:** Nick Slot 7 đã tồn tại trên máy, nhưng TikTok account switcher không settle trong 2 lần retry (`PROFILE_SWITCH_MAX_ATTEMPTS = 2`).
- **Kết luận: LỖI THỰC.** Fix: tăng MAX_ATTEMPTS lên 3. (Chi tiết: `tiktok-workbook-slot-mapping/references/profile-switcher-max-attempts-fix-20260909.md`)

## Cách đọc log để phân loại nhanh

```bash
# Đọc log mới nhất từ .ai-runs/
ls -lt ".ai-runs" | head -5
# -> lấy run mới nhất

# Đếm từng signature trong log.jsonl của batch
grep -c "is empty (no username)" ".ai-runs/<run>/log.jsonl"
grep -c "still mismatched after switch" ".ai-runs/<run>/log.jsonl"
```

Mẫu entry log cho "bình thường":
```json
{"result": "config-error", "extra": {"blocker_type": "script-blocker", "stop_reason": "account row 7 is empty (no username) for machine 1, skipping"}}
```

Mẫu entry log cho "lỗi thực":
```json
{"result": "manual-needed", "extra": {"blocker_type": "script-blocker", "stop_reason": "profile username still mismatched after switch"}}
```

## Quy tắc chung

- **"Config-error" + "script-blocker" + "empty"** → Thường là thiết kế (slot chưa có nick). Xem doc slot để confirm.
- **"Manual-needed" + "script-blocker" + nội dung logic** → Lỗi thực trong flow automation.
- **"Blocked-proxy-vpn"** → Vấn đề connectivity, không phải bug code.

Phân loại xong mới dispatch worker — chỉ dispatch cho signature "lỗi thực".

## Parity Schedule (dùng để tính Row từ timestamp alert)

| Ngày   | Ca 1 (06:00) | Ca 2 (12:30) | Ca 3 (19:00) | Đêm (01:00) |
|--------|-------------|-------------|-------------|------------|
| Lẻ     | Row 1       | Row 3       | Row 5       | Row 7      |
| Chẵn   | Row 2       | Row 4       | Row 6       | Row 8      |

Dùng `ZoneInfo("Asia/Ho_Chi_Minh")` để xác định ngày chẵn/lẻ — CẤM dùng `datetime.now()` trần (lệch timezone).
