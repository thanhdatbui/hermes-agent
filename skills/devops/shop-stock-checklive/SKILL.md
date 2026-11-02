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
- **checkmail.live** (Playwright / Chrome CDP) | Gmail | ✅ Siêu tốc (~1s/batch), nhận diện chính xác Live vs Die | Cần đăng nhập session trên web, gọi `CheckEmail()`. BẮT BUỘC dùng canonical runner `D:/Taadaa/GPM auto/scripts/run_checkmail_kibe_farm.py` (tự động login, cấp session, submit batch & trích xuất kết quả). TUYỆT ĐỐI KHÔNG tự viết script probe chay hay dùng Playwright không session vì trang bắt buộc có `api_key` mới chạy. Tránh chạy 2 script cùng lúc tranh chấp `checkmail_proxy_data` (gây crash decrypt key).
| On-device `automation_core.google_health` | Gmail | ⚠️ CẤM DÙNG LÀM PRIMARY CHECK: Chỉ bắt được popup CAPTCHA/Relogin trên UI; tài khoản bị khóa/disable ngầm backend vẫn trả `target_account_not_verified` (ngộ nhận LIVE). BẮT BUỘC dùng checkmail.live để check live Gmail. | Chạy trực tiếp trên thiết bị Android farm |

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
