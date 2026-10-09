# Farm Telegram Guardrail & Alerts Rulebook

## Protected Group Sinks

- **Nhóm Report Cron Taadaa Farm** (`-5188753741`): Bị guardrail khóa chặt. Chỉ cho phép gửi tự động khi `EXEC_MODE=CRON_AUTOMATED` (hoặc bypass khẩn cấp khi `ALLOW_CRON_SINK_OVERRIDE=1`).
- **Nhóm Farm Alerts Telegram group** (`-5373649734`): Là sink mặc định của farm machine alerts (`DEFAULT_ALERT_CHAT_ID`). KHÔNG đưa vào `PROTECTED_CRON_CHAT_IDS` vì sẽ gây breaking change, chặn mất machine alerts khi chạy thủ công hoặc test.

## Execution Guardrail Pattern (`_assert_cron_sink_allowed`)

```python
PROTECTED_CRON_CHAT_IDS = frozenset({
    "-5188753741",  # Nhóm Report Cron Taadaa Farm
})

def _assert_cron_sink_allowed(chat_id: str | int) -> None:
    s_chat_id = str(chat_id).strip()
    if s_chat_id in PROTECTED_CRON_CHAT_IDS:
        if os.environ.get("ALLOW_CRON_SINK_OVERRIDE") == "1":
            log.warning(f"[GUARDRAIL OVERRIDE] chat_id={s_chat_id} bypassed by ALLOW_CRON_SINK_OVERRIDE")
            return
        exec_mode = os.environ.get("EXEC_MODE", "").strip().upper()
        if exec_mode != "CRON_AUTOMATED":
            raise TelegramPermissionError(
                f"[GUARDRAIL BLOCKED] chat_id={s_chat_id} thuộc nhóm Cron bảo vệ nghiêm ngặt..."
            )
```

## Unit Test Checklist

Khi sửa đổi Telegram alert hay guardrail:
1. Đặt `import pytest` và test library lên đầu file test theo chuẩn PEP 8.
2. Test cả string chat_id (`"-5188753741"`) lẫn integer chat_id (`-5188753741`).
3. Test case-insensitive của `EXEC_MODE` (`CRON_AUTOMATED`, `cron_automated`).
4. Test flag override `ALLOW_CRON_SINK_OVERRIDE=1` và đảm bảo log warning được ghi nhận.
5. Test cả 2 hàm gửi: `_send_telegram_photo` và `_send_telegram_text`.
6. Chạy pytest với PYTHONPATH trỏ về `src/`:
   `PYTHONPATH=D:/Taadaa/automation-core/src pytest tests/test_alerts.py -v`

---

## Per-Workflow / Per-Repo Telegram Alert Routing (INVARIANT)

**Quy tắc định tuyến thông báo Telegram theo Script/Repo:**
CẤM dồn tất cả alert/report từ các repo vào một nhóm chung `Farm Alerts` (`-5373649734`).

1. **Alert/Report của script/quy trình nào BẮT BUỘC đẩy về đúng nhóm Telegram của repo đó:**
   - Nuôi Acc / Lướt Feed (`tiktok-luot nuoi acc` / `multi-machine-feed-session`) ➔ **Tiktok Luot Nuoi Acc** (`-5377611430`)
   - Đăng Video / Upload Avatar (`Tiktok-video`) ➔ **Tiktok video** (`-5435853713`)
   - Bật 2FA TikTok (`tiktok-add-bao-mat-f2a`) ➔ **Tiktok add 2fa** (`-5468653590`)
   - Follow TikTok (`tiktok-follow`) ➔ **Tiktok Follow** (`-5127276494`)
   - Đăng Ký TikTok (`Tiktok_Reg`) ➔ **Tikok Reg** (`-5494641602`)
   - Đăng Ký Gmail (`register gmail`) ➔ **Gmai reg** (`-5139245637`)
   - Đăng Nhập TikTok (`tiktok-log-in`) ➔ **Tiktok Log In** (`-5145780745`)
   - Gán Proxy (`gan-proxy`) ➔ **gan proxy** (`-5468841134`)
   - GPM Automation (`GPM auto`) ➔ **GPM Auto** (`-5256944036`)
   - Hotmail Automation (`Hotmail`) ➔ **hotmail** (`-5583559484`)
   - Automation Core hạ tầng (`automation-core`) ➔ **Automation Core** (`-5331653038`)

2. **Fallback về `Farm Alerts` (`-5373649734`):**
   - CHỈ áp dụng cho các script bảo trì hạ tầng dùng chung không thuộc repo riêng (PC reboot, sync mây OneDrive, tắt process rảnh...) hoặc không có nhóm Telegram chuyên biệt cho repo đó.

3. **Cấu hình Cron Jobs (`jobs.json`):**
   - Thuộc tính `deliver` của từng job watchdog BẮT BUỘC trỏ về đúng nhóm Telegram chuyên biệt của repo (ví dụ `tiktok-feed-session-watchdog` deliver về `telegram:-5377611430`).

