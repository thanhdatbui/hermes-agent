---
name: shop-stock-checklive
description: Check-live (kiểm tra live) automation cho kho tài khoản trên shop SHOPCLONE7 (doravo.net) — nguồn TikTok/IG/Gmail/Hotmail/X, dọn product_stock→product_die có backup, VPS direct TikTok check, GH Actions artifact flow, web tools clonefbig/khommo247. Use when building/running/debugging check-live cron hoặc 'check live/dọn kho' cho shop acc.
---

# Check-live tự động kho tài khoản (SHOPCLONE7 / doravo.net)

## Trigger
- User nhờ: "check live", "kiểm tra live", "dọn kho", "chạy check hàng ngày" cho shop acc.
- Hàng up tay: `supplier_id = 0` — kho local bảng `product_stock`; acc die chuyển `product_die`.

## Workflow chuẩn (chạy production 2026-08-20)
1. **Xác định SP đích**: query DB qua SSH: `SELECT id,name,cost,price,status FROM products WHERE supplier_id=0` (SP up tay: 40 TikTok, 57 IG 2FA, 38/39/60/61...).
2. **Lấy stock**: JOIN `product_stock` với `products` theo `product_code = code`. Cột `uid` = username/email để check; `account` = chuỗi đầy đủ (giữ nguyên khi chuyển die).
3. **Backup TRƯỚC khi xóa**: `mkdir -p /var/www/shopclone7/backups/<ten>/<ts>` + dump TSV các bản ghi sẽ xóa (đã có backup pre-tt-clean-die/product_die).
4. **Check live theo nguồn** (ma trận dưới).
5. **Dọn DIE**: INSERT `product_die` (product_code, seller, uid, account, create_gettime, type) rồi DELETE `product_stock` — chunk 200, transaction. TRƯỚC khi xóa hàng loạt: verify mẫu DIE bằng nguồn độc lập (retry cao hơn / browser) — tránh dọn nhầm acc live.
6. **Báo cáo**: LIVE / DIE đã dọn / UNKNOWN còn lại.

## Nguồn check live — ma trận quyết định (cập nhật 2026-08-20)
| Nguồn | Nền tảng | Kết quả thực tế | Ghi chú |
|---|---|---|---|
| **VPS direct tiktok.com** (JSON rehydration) | TikTok | ✅ ~98% phân loại; UNKNOWN 377→9 với retry 4→8→12 | Không login, không web 3 — ƯU TIÊN |
| GitHub Actions (`thanhdatbui/tiktok_check_live`) | TikTok | ⚠️ 77% UNKNOWN (runner IP datacenter bị WAF) | Chỉ dùng khi cần; có fix 401 artifact |
| clonefbig.com/checklive (Playwright headful) | Instagram | ✅ qua CF Turnstile tự tick (IP dân cư) | `#inputArea` + `startCheck()` |
- **checkmail.live** (Playwright / Chrome CDP) | Gmail | ✅ Siêu tốc (~1s/batch), nhận diện chính xác Live vs Die | Cần đăng nhập session trên web, gọi `CheckEmail()`. Tương tác qua `window.editor.setValue(emails_text)` rồi `document.getElementById('btn-check').click()`. Đọc kết quả qua `window.liveResultEditor.getValue()` — parse `[Live]`/`[die]` từng dòng bằng regex. |
| khommo247.com/cong-cu/check-tiktok | TikTok | ⛔ BẮT BUỘC ĐĂNG NHẬP (tool-login-gate) + CF chặn datacenter/mobile-proxy | Cần tài khoản + IP dân cư |
| On-device `automation_core.google_health` | Gmail | ✅ Phân loại LIVE / CAPTCHA / RELOGIN | Chạy trực tiếp trên thiết bị Android farm |

## checkmail.live — Cách tương tác đúng qua CDP (2026-09-02)

Trang dùng **CodeMirror** editor thay vì plain `<textarea>` — `page.fill('#input-mail')` sẽ timeout vì element `is not visible`.

```python
# 1. Set input qua CodeMirror JS API:
page.evaluate("""(payload) => {
    if (window.editor) { window.editor.setValue(payload); }
    document.getElementById('btn-check').click();
}""", emails_text)  # truyền emails_text qua argument, tránh newline bên trong JS string literal

# 2. Poll kết quả qua liveResultEditor:
data = page.evaluate("""() => {
    return {
        live: window.liveResultEditor ? window.liveResultEditor.getValue() : '',
        btn_text: document.getElementById('btn-check').innerText.trim()
    };
}""")

# 3. Parse mỗi dòng: '[Live] email@gmail.com' hoặc '[die] email@gmail.com'
import re
for line in data['live'].split('\n'):
    m = re.search(r'([a-zA-Z0-9._%+-]+@gmail\.com)', line, re.I)
    if m:
        if '[live]' in line.lower(): live_list.append(m.group(1))
        elif '[die]' in line.lower(): die_list.append(m.group(1))
```

**Pitfall:** Đừng nhúng newline (`\n`) trực tiếp bên trong JS string template khi dùng `page.evaluate("""...""")` — Playwright sẽ báo `SyntaxError: Invalid or unexpected token`. Luôn truyền payload qua argument thứ 2 của `evaluate(js_code, arg)`.

## Pitfalls (đắt tiền nhất)
- **checkmail.live dùng CodeMirror không phải textarea thuần:** `page.fill('#input-mail')` hoặc `page.evaluate('... \n ... ')` inline đều fail. Xem section "Cách tương tác đúng qua CDP" ở trên.
- **GH Actions runner = IP datacenter → TikTok WAF chặn ~77%**; đừng kết luận acc die từ kết quả đó. Chuyển VPS direct.
- **GH artifact download 401**: API trả 302 sang signed URL và DROP Authorization → urllib tự re-send header → 401. Fix: redirect handler strip auth (code trong references/checklive-sources.md).
- **Camoufox proxy**: bắt buộc dict `{"server": "...", "username": ..., "password": ...}`; nhét creds vào server URL → `NS_ERROR_PROXY_CONNECTION_REFUSED` dù curl vẫn OK.
- **Camoufox headless bị CF chặn (Just a moment), headful qua được** — khommo247, kể cả trên VPS qua Xvfb.
- **khommo247 nút "Để sau" (modal .tool-login-gate) chỉ đóng UI — backend KHÔNG chạy check** (kết quả rỗng). Phải login thật: `/dang-nhap?return=...`, fields `loginEmail` + `loginPass`.
- **IP quyết định CF, không phải browser**: IP dân cư ✅ / datacenter VPS ❌ / proxy mobile farm ❌ (egress bị flag proxy). Không có browser nào cứu IP bị flag.
- **Mobile proxy pass chứa `#`** → URL-encode `%23` khi nhét vào URL. Pass login panel (`n0spam@@`) KHÁC pass proxy client (`TaadaaMobi#2026!` trong PROXYgandienthoai.xlsx) — đừng nhầm.
- **Cron GH Actions check 487 acc mất ~35 phút** → poll timeout ≥60 phút mới đủ.
- **Cookies DB của Chrome profile đang chạy bị lock** — không copy được; dùng CDP thay vì đọc file.
- **Isolate lỗi từng SP trong batch checklive**: Trong runner checklive tổng hợp nhiều SP (`daily_manual_stock_checklive.py`), bắt buộc bọc `try/except` độc lập cho từng SP. Lỗi timeout/cookie của một bên (ví dụ khommo247 của TikTok) tuyệt đối không được làm crash toàn bộ tiến trình khiến các SP khác (IG qua clonefbig, kiểm đếm stock SP tĩnh) bị hủy và không cập nhật/gửi báo cáo. Báo cáo Telegram phải phản ánh đúng các SP đã check thành công và đánh dấu fail riêng cho SP gặp sự cố mạng/cookie.
- **Lệch tồn kho so với 'đã bán hôm qua' (Stock delta vs sold_yesterday divergence)**: Khi báo cáo ghi giảm tồn `delta` nhiều hơn `sold_yesterday`:
  1. Kiểm tra thời điểm lưu state thành công gần nhất (`checklive_state.json` hoặc log cron `output/1cb63d617582/*.md`). Nếu cron ngày hôm trước bị crash/bỏ lỡ, mốc so sánh `prev_stock` là từ 2+ ngày trước.
  2. `sold_yesterday` trong SQL chỉ quét đúng 1 ngày lịch dương (`CURDATE() - 1`). Muốn đối chiếu chính xác, query `product_order` từ mốc thời gian lưu state cũ đến hiện tại và cộng với số lượng `product_die` dọn trong khoảng đó: `delta = SUM(amount_period) + SUM(die_cleaned)`.

- **CloneFBIG API `buy_product` cắt cụt token OAuth2 (2026-08-29)**:
  - Khi mua Hotmail/Outlook Graph API trên `clonefbig.com` qua API `/api/buy_product`, chuỗi token trả về trong JSON bị cắt ngắn (chỉ còn ~101 ký tự thay vì ~457-500 ký tự chuẩn Microsoft MSA Artifacts) do format API của shop bị giới hạn.
  - Token đầy đủ 100% được lưu nguyên vẹn trong Web UI (thuộc tính `data-checkbox` hoặc bảng lịch sử đơn hàng `/product-orders`).
  - Khi mua hoặc lấy token từ CloneFBIG: Bắt buộc lấy qua CDP/Web UI (DOM table / `data-checkbox`) thay vì chỉ gọi qua endpoint `api/buy_product`.

## Setup DB + cron
- `ssh -i ~/.ssh/doravo_deploy root@152.42.187.200`; đọc `/root/.shopclone7_db_credentials` (DB_HOST/DB_USER/DB_PASSWORD/DB_NAME); `mysql -h$HOST -u$USER -p$PWD $DB -N -e "..."` qua SSH.
- Hermes cron daily: script `C:/Users/Kibe/AppData/Local/hermes/scripts/daily_manual_stock_checklive.py` (V2: TikTok VPS-direct 2 vòng retry 8→12 + IG clonefbig), `0 7 * * *`.
- Hermes browser CDP: Chrome profile `$HERMES_HOME/browser_profile` chạy `--remote-debugging-port=9222`; `playwright connect_over_cdp("http://127.0.0.1:9222")` chia sẻ cookies/cf_clearance — kết nối được kể cả khi session khác đang giữ profile.

## References
- `references/checklive-sources.md` — từng nguồn chi tiết + code (TikTok direct VPS, GH Actions + fix 401, clonefbig, khommo247 selectors/gate).
- `references/checklive-runner-failure-isolation.md` — Quy tắc bọc try/except độc lập cho từng SP trong runner tổng hợp, chống crash lan sang các bên còn lại khi 1 site timeout (2026-08-28).
- `references/mobiproxy-panel-api.md` — panel MobiProxy (test.taadaa.click): login riêng, API proxy_check/getlist/getip, api.php actions.