# ATX-agent JSON-RPC API (farm S7, atx-agent 0.10.1) — reverse-engineered 2026-08-16

**User rule (16/08, angry correction): ATX-agent là PRIMARY đọc UI dump. CẤM gọi `uiautomator dump` trực tiếp bằng tay.** Trên máy S7 yếu (Android 8), `uiautomator dump` thường bị **Killed** (OOM) → dump rỗng/tool không có XML. `capture_ui_xml` của automation_core gọi uiautomator trước → fail `non_xml_ui_dump`. Phải đi qua ATX-agent.

## Kiểm tra ATX đang chạy + forward

```bash
adb -s <serial> shell "ps -A | grep -iE 'atx|agent'"   # atx-agent + apkagent.cli phải có
adb -s <serial> forward tcp:7912 tcp:7912               # -> in ra 7912
curl -s http://127.0.0.1:7912/version                  # 0.10.1
curl -s http://127.0.0.1:7912/info                     # udid/model/sdk/display 1080x1920
```

## Endpoint JSON-RPC — ĐÚNG và SAI

| Endpoint | Kết quả |
|---|---|
| `POST /jsonrpc/0` (JSON-RPC cũ) | `method not found` với MỌI method — sai |
| `POST /wd/hub/session` (WebDriver cũ) | `404 page not found` — sai |
| `POST /session/{pid}:com.github.uiautomator/jsonrpc/0` | ✅ ĐÚNG |

`{pid}` = pid của process **`com.github.uiautomator`** (service UIAutomator), KHÔNG phải pid atx-agent.
Lấy: `adb shell "ps -A | grep com.github.uiautomator"` (vd `u0_a184 11246 ...`). Cảnh báo nếu dùng pid atx-agent (`/data/local/tmp/atx-agent server -d --stop`): lỗi `cmdline expect [com.github.uiautomator] but got [...]`.

## Method hoạt động (gọi bằng requests, JSON body)

```python
BASE = f"http://127.0.0.1:7912/session/{pid}:com.github.uiautomator/jsonrpc/0"
def call(method, params):
    return requests.post(BASE, json={"jsonrpc":"2.0","id":1,"method":method,"params":params}, timeout=30).json()
```

| Method | Params | Kết quả |
|---|---|---|
| `dumpWindowHierarchy` | **`[true]`** (bắt buộc) | JSON `result` = nguyên XML hierarchy (text/resource-id/class/bounds) |
| `click` | `[x, y]` | `result: true` — tap hoạt động tốt |
| `setText` | `[text, true]` hoặc selector | Chỉ với Android view thật; **WebView field → `UiObjectNotFoundException`** (WebView không expose EditText) |
| `text` / `input` / `typeText` / `setValue` / `sendKeys` | — | `method not found` — KHÔNG có |
| `back` | — | `method not found` → dùng `adb shell input keyevent 4` |
| `dumpHierarchy` | — | `method not found` (tên đúng là `dumpWindowHierarchy`) |

`dumpWindowHierarchy` với `params:[true]` là key — các params khác (`[]`, `null`) → `method parameters invalid`.

## Gõ text vào WebView (Microsoft login) — con đường đúng

ATX không gõ được vào WebView field (setText không tìm thấy node). Làm vậy:
1. `click` vào field (lấy bounds từ dumpWindowHierarchy)
2. Xác nhận IME focus: `adb shell dumpsys input_method | grep mInputShown` → `mInputShown=true` + `mServedView=...WebView`
3. `adb shell input text '<pass>'` — gõ được, ký tự ● hiện trong field
4. Tap nút submit bằng `click` (hoặc `input keyevent 66` nếu tap không ăn)

## Trình tự login Outlook app bằng ATX (máy 31, acc shop chưa qua dịch vụ, 16/08)

1. Onboarding ("Được kết nối và bảo vệ"): tap `btn_primary_button` THÊM TÀI KHOẢN
2. **"Chọn loại tài khoản"** (`ChooseAccountActivity`): entry Outlook = `btn_add_account_outlook` bounds `[360,384][720,768]` → click `(540,576)`. (LƯU Ý: runner cũ chết `OUTLOOK_APP_PASSWORD_FIELD_NOT_FOUND` vì tap_text "Outlook" không land — entry button KHÔNG có text, chỉ có resource-id!)
3. WebView Microsoft: email **pre-filled** (identityBadge + bannerText = email) → màn "Nhập mật khẩu"
4. Field mật khẩu ~`(540,690)` → click → `input text` → tap "Tiếp theo" `(540,1011)`
5. `AddAnotherAccountActivity` ("Thêm một tài khoản khác?", "Bạn muốn thêm một khoản khác không?") → tap "CÓ LẼ ĐỂ SAU" `(180,1836)`
6. Inbox: `Hộp thư đến` + empty-state "Đã xong công việc hôm nay" → SUCCESS
7. **Verify acc active bằng drawer** (user rule): click `account_button` (36,96)–(156,216) → `drawer_header_summary` = email target. Đóng drawer: `input keyevent 4` (ATX không có `back`).

## Ghi chú

- Acc hotmail shop **chưa qua dịch vụ** (loại boxtaikhoan GraphAPI 262đ) **login thẳng, KHÔNG dính account protection** — khác acc farm cũ (máy 38/54 phải điền mail khôi phục). Kiểm tra từng acc: nếu dính "Hãy bảo vệ tài khoản" mới cần flow recovery.
- ATX dump thấy node SystemUI (battery/clock) như mọi dump — lọc như automation_core đã làm.