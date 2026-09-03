---
name: web-marketplace-research
description: Research products/prices/catalog on web shops & marketplaces (especially bot-protected Chinese sites selling digital accounts). Browser-first scraping workflow, DOM-only extraction, policy-page reading. Use when user asks to "nghiên cứu sản phẩm" / research a shop site / compare account suppliers.
---

# Web Marketplace / Product Research

Khi user đưa link shop/marketplace (thường là chợ bán tài khoản TQ: Twitter/X, TikTok, Telegram, Gmail, IG, FB...) và nhờ nghiên cứu sản phẩm/giá. User cần: tổng hợp danh mục + giá + tồn kho + chính sách, báo cáo tiếng Việt ngắn gọn (xem Output).

## Workflow

1. **Thử curl trước** cho trang đơn giản (plain HTML). Nếu http=200 nhưng size=0 hoặc exit code lạ → **bot protection, bỏ curl ngay**, dùng browser stack.
2. **browser_navigate** vào trang chủ → snapshot cho cấu trúc + sidebar danh mục. Lấy toàn bộ link danh mục bằng browser_console (DOM-only, được phép):
   ```js
   JSON.stringify(Array.from(document.querySelectorAll('a')).map(a => ({t: a.innerText.trim().slice(0,40), h: a.href})).filter(x => x.h && !x.h.startsWith('javascript')))
   ```
   → có URL pattern: `/category/<slug>.html`, `/products/<slug>.html`, `/news/item/<slug>`.
3. **Navigate thẳng vào từng category URL** (không click qua menu) — snapshot trả bảng sản phẩm ngay. Bảng chuẩn chợ acc TQ: cột `商品名称 | 价格 | 库存 | 已售 | 购买` (name | price | stock | sold).
4. Ưu tiên các danh mục liên quan user: với farm TikTok → TikTok, Telegram (API接码), Gmail, số ảo. Đừng quét hết 15+ category — đủ để trả lời.
5. **Policy pages** (支付说明/售后说明/退款政策): snapshot hiện heading nhưng paragraph RỖNG (nội dung ẩn). Đọc trực tiếp:
   ```js
   (() => { const art = document.querySelector('article'); return art ? art.innerText.slice(0, 3000) : 'NO ARTICLE'; })()
   ```
6. **Product detail** nếu cần format giao hàng: navigate `/products/<slug>.html`, snapshot có form mua + "暂时无货" nếu hết hàng + mô tả.
7. Tổng hợp → báo cáo (Output bên dưới). Offer đào sâu category cụ thể.

## Pitfalls

- **curl bị bot-block**: http 200 + size_download=0 → đừng mất thời gian thêm header/cookie, chuyển browser ngay.
- **browser_console KHÔNG được dùng `fetch`/network** — bị chặn "sensitive browser JavaScript primitive". Chỉ dùng DOM reads: querySelectorAll, innerText, JSON.stringify. Nếu cần nhiều page, navigate từng cái.
- Snapshot bảng lớn bị truncate (~4k dòng) — navigate theo category thay vì đổ hết /products.
- **Link sp trên tuitehao là `/item?id=<N>`** (VD sp IG 全球账号 = `https://www.tuitehao.cc/item?id=1380`, sp No-2FA = id=1379), KHÔNG phải `/products/<slug>.html`. Tên slug tiếng Anh (`instagram-new-no-email-2fa.html`) có thể trỏ sp KHÁC với tên tiếng Trung hiển thị — đừng gán tên tiếng Trung cho URL slug gần nghĩa. Lấy link chính xác bằng DOM: iterate `document.querySelectorAll('tr')`, tìm row chứa text tiếng Trung cần, đọc `a[href*="/item?id="]` bên trong row — snapshot/`a`-only không ra vì text nằm trong cell lồng.
- **tuitehao KHÔNG có search URL**: `/search?keyword=...` redirect về trang order-lookup (vô dụng). Vào thẳng `/category/<slug>.html` — lấy link category thật từ menu dropdown bằng DOM trang chủ (`querySelectorAll('a[href*="/category/"]')`); slug mẫu: `facebook-new-account.html` = Facebook新号, `twitter.html` = X-Twitter新号, `instagram-new-account.html` = IG新号, `facebook-account.html` = Facebook tổng. Bảng category dài (50+ sp) bị snapshot truncate → dump CẢ bảng 1 lần bằng browser_console: `JSON.stringify(Array.from(document.querySelectorAll('tr')).map(tr => { const c = tr.querySelectorAll('td'); ... return {n: tên, p: giá, s: stock, d: đã bán, h: link item}; }))` — đủ để lọc nhanh theo stock/loại mà không cần navigate từng sp.
- Product detail page hiện nút `暂时无货` (temporarily out of stock) khi hết hàng; "相似商品推荐" (similar products) là cách tìm sp cùng loại có link thật.
- Không tin "已售" (sold) mù quáng — 0 có thể là sản phẩm mới; số bán cao + tồn cao = sản phẩm chủ lực thật.
- Giá luôn ¥ (CNY); đổi sang VND/USD để user dễ so (¥1 ≈ 3.5k VND ≈ $0.14).
- Chợ acc TQ: thanh toán chủ yếu USDT, balance không rút/không hoàn, bảo hành chỉ "bao first login 24h" — KHÔNG bảo hành khi dùng proxy chung/đa acc 1 IP (đúng case farm). Luôn nêu rủi ro này trong báo cáo.

## Phát hiện 2 shop cùng một kho nguồn (stock matching)

Khi user nghi shop X bán đúng hàng user đang lấy từ nguồn Y (vd tuitehao.cc vs clonefbig): đối chiếu bằng (tên phân loại gần giống + số tồn kho gần bằng). **Stock trùng ±1–2 con (109.677 vs 109.678; 21.164 = 21.164; 4.706 vs 4.707) = cùng kho nguồn** — chênh do có người mua giữa 2 lần đọc. Bằng chứng stock mạnh hơn tên sp (2 shop đặt tên khác ngôn ngữ). Các bước:
1. Probe catalog nguồn thật của user qua API live (đọc key từ DB, không in secret).
2. Scrape shop kia bằng browser (bot-block → bỏ curl, dùng browser stack).
3. Map theo đặc tả khớp: temp mail (TempMail.Plus/Smvmail/Fvia), UID 6157x, 282 unlock, khoảng aged (1–7/8–15/15–30/30–180 ngày), 2FA on/off + stock.
4. Trình bày dạng cặp bảng: shop A (giá/stock) ↔ nguồn user (giá bán/cost/stock). Giá 2 shop cùng nguồn khác nhau là bình thường (markup khác nhau — VD tuitehao bán lẻ 2.3–3.6× cost user).
5. Kết luận theo vai user: nếu shop kia là khách sỉ mua từ ông anh user (bán lại TQ) → dùng làm bảng giá thị trường, không coi là đối thủ cần đánh bại.

### Test link giữa 2 shop (có mirror hay chỉ chung nguồn)

Stock khớp chỉ chứng minh "chung kho nguồn", KHÔNG chứng minh shop B mirror shop A. Muốn chứng minh/loại trừ link tự động: **hide-test** — ẩn 1 sp bên A (backup trước), chờ 1 chu kỳ sync (~8–10 phút; theo dõi stock tick của sp để biết sync có chạy), reload B check sp tương ứng; rồi bật lại A ngay. Kết quả thật 2026-08-15: ẩn doravo ID 56 (IG 全球 2FA) → tuitehao sp 全球账号 VẪN hiện, stock vẫn chảy (109.644→109.508, 已售 88→89) → KHÔNG mirror, chỉ chung upstream clonefbig. Cảnh báo: test này làm ẩn sp bán hàng thật trong ~10 phút — phải backup + bật lại ngay, và xin phép user trước vì có thể ảnh hưởng doanh thu.

### Báo cáo chứng minh "cùng kho nguồn" (kèm link + bản dịch)

Khi user cần báo cáo để gửi đối tác/người trên, chứng minh shop B lấy hàng từ nguồn user A: cấu trúc chuẩn (đã được chấp nhận 2026-08-15):
1. **Mỗi sp 1 block**: tên sp bên A (nguồn, kiểu clonefbig) + giá gốc + stock live ↔ sp tương ứng bên B (tên tiếng Trung + **bản dịch sang kiểu clonefbig trong ngoặc** — user không đọc TQ, cần dịch để thấy khớp) + giá + stock live. Kèm **link đầy đủ 2 bên** (B: `https://www.tuitehao.cc/item?id=N`; A: link API/trang sp).
2. **Bảng stock song song**: stock nguồn vs stock B cùng thời điểm (chênh vài chục con = trôi realtime, cùng kho).
3. **Loại trừ các nguồn nghi vấn khác**: nếu user nghi shop B lấy từ trang X/Y, check từng trang và kết luận rõ "có/không phải nguồn" kèm lý do (VD trustvia.net = proxy/VPN/TikTok không có IG; accsmtp.com = shop acc quốc tế nhưng IG toàn loại firstmail.ltd/followers, không có sp no-email stock 100k+ → không phải).
4. Kết luận 1 câu: "cùng một kho hàng → B (hoặc nhà cung cấp B) lấy trực tiếp từ A".

## Công cụ web check-live (khommo247, clonefbig) — findings 2026-08-20

Khi user nhờ check qua tool web của bên thứ 3 (khommo247 check-tiktok, clonefbig checklive) bằng cron tự động:
- **khommo247.com/cong-cu/check-tiktok**: CF Managed Challenge chặn mọi IP không phải dân cư thật — IP nhà qua được (Camoufox headful, không phải headless), IP VPS datacenter và proxy mobile farm đều "Just a moment". Selector: `#ttList` (nhập username) + `#ttBtnStart` ("Check tất cả"). **BẮT BUỘC đăng nhập**: bấm check → modal `.tool-login-gate` "Yêu cầu đăng nhập"; nút "Để sau" chỉ đóng UI (backend không chạy), phải login thật (`/dang-nhap`, fields `loginEmail`/`loginPass`, CSRF `_csrf`). Trang multi-tool: mỗi tool 1 textarea riêng (`#ttList` cho TikTok), textarea của tool ẩn (`telegramOtpProxy`...) không fill được — dùng đúng id.
- **clonefbig.com/checklive** (IG): CF Turnstile tự tick qua được với IP dân cư; `#inputArea` (1 user/dòng) → `startCheck()` → đọc `#liveCount`/`#dieCount`/`#liveOutput`/`#dieOutput`.
- Quy tắc chung (sửa 2026-08-20 sau test chéo host×IP): **host/fingerprint + IP kết hợp quyết định CF** — IP dân cư qua khi browser chạy trên máy fingerprint thật (máy nhà); datacenter ❌ ngay cả cùng Camoufox headful; proxy mobile farm `test.taadaa.click:51xx` (IP PPPoE dân cư) chỉ qua được khi browser chạy trên MÁY NHÀ (Camoufox ≥0.5.5 headful, proxy dict username/password tách, KHÔNG `geoip=True`) — browser chạy trên VPS dù egress qua cùng farm vẫn `CF_BLOCK` (sweep 32 port toàn fail). Đừng hứa tích hợp web tool có login-gate vào cron VPS trước khi test login thật + host/IP thật. Recipe đầy đủ + recon panel MobiProxy: skill `shopclone7-site-ops` → `references/khommo247-home-machine-proxy-recipe-2026-08.md`.

Chi tiết từng nguồn khác (TikTok VPS direct, GH Actions fix 401, Camoufox proxy dict, MobiProxy panel, dọn product_stock→product_die có backup): xem skill `shop-stock-checklive`.

## Shop Việt Nam (boxtaikhoan.com) — hotmail/outlook 2 tier (2026-08-16)

Shop acc MMO Việt (giá VND "đ", `boxtaikhoan.com@gmail.com`, Zalo/Telegram, WooCommerce-style). Category page: `https://boxtaikhoan.com/category/<danh-muc>`; product URL dạng `/product/<slug><id>` (không phải `/item?id=` kiểu tuitehao). **"Chi tiết sản phẩm" tab RỖNG** — phần dài dưới tab là warranty template DÙNG CHUNG mọi sản phẩm (cùng chính sách bảo hành clone 24h, "4 nguyên nhân kill clone" gồm cảnh báo farm: VPN/proxy bẩn, nuôi nhiều clone 1 IP, login tool auto không ổn định...). Facts thật nằm ở (a) heading dài + (b) dòng summary ngắn dưới giá + (c) dòng "Định dạng : ...".

**Hotmail bán sỉ 2 tier — phân biệt (quan trọng cho bài toán đọc OTP):**
- **Tier rẻ "TRUSTED GraphAPI - Live Vĩnh Viễn, MailKP fviainboxes, Chưa Qua Dịch Vụ"** (262đ, kho 44k): acc thường live dài, mail khôi phục = temp mail fviainboxes, KHÔNG công bố token → muốn đọc mail/OTP vẫn kẹt IMAP basic auth đã chết → chỉ đọc được qua UI (Outlook app path).
- **Tier đắt "Trust - OAuth2 [IMAP/POP3/GRAPH] Live 12-36 Months, Zin 100%, Còn Skip 7 Ngày"** (393đ, kho 118k): dòng **"Định dạng : mail|pass|refresh_token|client_id"** là tell — kèm refresh_token+client_id → đọc mail qua **Graph API** không cần password, bypass cả basic-auth-dead lẫn recovery-OTP shared. "Còn Skip 7 ngày" = còn trong cửa sổ bảo hành (không đổi thông tin 7 ngày đầu theo chính sách clone). Khi user cần tự động đọc OTP hotmail số lượng lớn, tier có token đáng giá hơn dù đắt hơn ~1.5×.

Chi tiết 2 sản phẩm + lập luận: `references/boxtaikhoan-hotmail-2026-08-16.md`.

## Phân loại tài khoản TikTok trên thị trường MMO (Giỏ hàng vs Live vs 1k Follow)

Khi user yêu cầu nghiên cứu/tìm kiếm thực tế các gói bán tài khoản TikTok (trên TaphoaMMO, Telegram Store bot, chợ MMO):
- **Quy tắc phản hồi**: BẮT BUỘC tra cứu số liệu/bằng chứng quy trình cụ thể từ app/hệ thống thực tế, không trả lời chung chung lý thuyết suông. Nếu các web tìm kiếm bị bot-block, dùng proxy mobile farm (`mobi1:TaadaaMobi#2026!@test.taadaa.click:5101`) hoặc inspect trực tiếp qua tool để lấy facts.
- **3 phân loại sản phẩm thực tế trên thị trường**:
  1. **Acc Mở Giỏ Hàng - Không Live (~30k - 100k)**: Acc clone 0 follow lách liên kết với TikTok Shop Seller Center. Có tab Giỏ hàng để gắn link sản phẩm video nhưng KHÔNG CÓ NÚT LIVE (vì thiếu 1k follow).
  2. **Acc 1k Follow - Chưa mở Giỏ Hàng (~150k - 250k)**: Đã buff/nuôi đủ 1.000 followers → Đã mở tính năng Live, nhưng chưa đăng ký TikTok Shop Creator (người mua tự thao tác vào Creator Center bấm nhận).
  3. **Acc 1k Follow - Mở sẵn Giỏ hàng + Có Live (~350k - 500k)**: Đã có $\ge 1.000$ follow, đã đăng ký duyệt giỏ hàng Creator và đã được nhả quyền phát Live. Dùng được ngay cho Live Shopping (vừa live vừa ghim giỏ hàng).
- **Quy trình chuyển đổi từ (2) lên (3) trên App**:
  - Vào *Hồ sơ* → Menu 3 gạch → *Công cụ dành cho nhà sáng tạo (Creator Tools)* → *TikTok Shop cho nhà sáng tạo*.
  - Hệ thống tự động tích xanh 3 điều kiện (≥1k follow, ≥18 tuổi, không vi phạm) → Bấm *Xác nhận/Đăng ký* là tab Showcase (Giỏ hàng) mở ngay trong 1 phút, không cần KYC CCCD.
  - Nút LIVE đã có sẵn khi đạt 1k follow; khi live có thêm nút "Sản phẩm" để ghim link bán hàng.
- **Điểm phân biệt kỹ thuật**:
  - *Tự nuôi*: Đạt 1.000 follow sạch thì tự động đủ điều kiện cả 2 (Live hệ thống tự nhả sau 24-48h, Giỏ hàng Creator bấm đăng ký duyệt trong 1 phút).
  - *Mua chợ*: Người bán luôn tách giá theo 3 nhóm trên vì quy trình tạo và độ rủi ro khoá tính năng khác nhau.

## Sàn TMĐT Việt Nam (Shopee / TikTok Shop) — Anti-bot & Profile Handling (2026-08)

Khi user nhờ tìm kiếm/nghiên cứu sản phẩm trên Shopee / TikTok Shop:
- **Cơ chế chặn WAF/Anti-bot**: `shopee.vn/search` và URL sản phẩm tự động redirect về `shopee.vn/verify/traffic/error` (`is_logged_in=false`) nếu truy cập bằng trình duyệt tự động chưa có session hoặc bị cờ bot.
- **Shopee direct-source rule**:
  - Khi user yêu cầu Shopee, chỉ dùng dữ liệu từ live Shopee trên đúng tool/session mà user chỉ định. Không chuyển sang Google, snippets, cached pages, hoặc dữ liệu cũ để lấp khoảng trống.
  - Nếu Shopee trả `/verify/traffic`, `/verify/captcha`, `is_logged_in=false`, không render card, hoặc tool trả 0×0/missing window, báo `BLOCKED/UNVERIFIED`; không tiếp tục suy đoán.
  - Chỉ dùng CDP để đọc/thao tác Shopee khi user đã yêu cầu/cho phép CDP; browser plugin và `computer_use` là các bề mặt riêng, không tự hoán đổi.
  - **Lưu ý vòng đời tab CDP**: Sau khi cào xong, nếu đóng tab ngay (`Page.close`), người dùng sẽ không thấy tab Shopee lưu lại trên giao diện Chrome của họ; cần giải thích rõ nếu user hỏi về việc không thấy tab. Đồng thời kiểm tra đúng Profile đang mở trên port CDP để tránh nhầm instance không có cookie đăng nhập.
- **Nạp Profile Chrome có sẵn của User**:
  - Danh sách profile nằm tại `C:\Users\<user>\AppData\Local\Google\Chrome\User Data\Local State` (`profile.info_cache`).
  - Cookie lưu tại `Profile <N>\Network\Cookies`. Khi Chrome đang mở, file database này bị khóa (locked) — cần copy sang temp hoặc khởi động Chrome instance riêng với `--user-data-dir` và `--profile-directory`.
  - Tài khoản đã đăng nhập (`SPC_ST`, `SPC_U`) giúp vượt qua màn chặn `verify/traffic/error` của Shopee.
- **Đặc tả sản phẩm kỹ thuật**: Trả về đúng link thật từng sản phẩm, khoảng giá theo phân loại/mét, nêu rõ thông số kỹ thuật (Cat6 1Gbps / Cat7 10Gbps, lõi đồng UTP/STP) phù hợp đúng thiết bị người dùng đang kết nối (Router -> AP MikroTik / Switch).

## Output (theo style user)

- Tiếng Việt, ngắn, không dump nguyên văn EN/TQ.
- **Báo cáo đối chiếu / gửi đối tác: TUYỆT ĐỐI KHÔNG DÙNG ICON/EMOJI, TUYỆT ĐỐI KHÔNG TỰ KẾT LUẬN / SUY DIỄN / BÌNH LUẬN** (user phản ứng gắt: "k cần phải kết luận cặc gì cả chỉ đưa thông tin thôi", "bỏ hết mấy dòng ghi nguồn riêng TQ"). Chỉ đưa thông tin thuần túy (tên, giá, tồn kho, đã bán, link). Cấm tự ý chèn các câu suy đoán như "để anh đi deal giá gom hàng", "nó cắm API thẳng", "nguồn riêng TQ", "bằng chứng lấy từ xưởng khác", v.v.
- **Chỉ liệt kê dữ liệu thuần túy + link thực tế**: Mỗi sản phẩm phải ghi rõ tên gốc + bản dịch nghĩa tiếng Anh + link từng bên (nguồn, shop kia, shop mình) + giá + stock live. KHÔNG tự ý chèn nhận định/suy luận cá nhân khi user yêu cầu báo cáo thuần liệt kê.
- **Thứ tự trình bày / Thứ tự Sheet**:
  - Sheet 1: Danh sách các mặt hàng bán chạy (>1.000 đã bán) đưa lên đầu (bỏ toàn bộ cột ghi chú/kết luận nguồn gốc).
  - Sheet 2: Đối chiếu 3 bên (Tuitehao vs Doravo vs CloneFBIG) xếp phía sau.
  - Sheet 3: Đối chiếu danh mục với các site khác (trustvia, accsmtp).
- **Kỷ luật đối chiếu spec**: Tuyệt đối không gượng ép map các spec khác nhau thành cùng loại (ví dụ: "Random Username" ≠ "Random Country IP Reg"). Khi spec lệch phải tách riêng hoặc loại bỏ, không tự ý suy diễn.
- **Bắt buộc kèm LINK sản phẩm trực tiếp**: Khi user nhờ lướt sàn (Shopee, TikTok Shop, Taobao...), luôn phải trả về link cụ thể từng sản phẩm thật kèm giá/stock (dạng `shopee.vn/<name>-i.<shop_id>.<item_id>`), không chỉ liệt kê tên chung chung.
- **Soạn tin nhắn gửi đối tác / người trên**:
  - CỰC KỲ NGẮN GỌN (3-4 dòng tóm tắt các sheet có gì), KHÔNG lặp lại chi tiết đã có trong file Excel.
  - Không viết nhận xét, không kết luận thay, không kèm emoji, chỉ đưa thông tin thuần để người nhận tự xem file.
- **Thiết kế bảng Excel đối chiếu trực diện 3 bên**:
  - **Giới hạn tên Sheet**: Tên Sheet/Tab BẮT BUỘC <= 31 ký tự (chuẩn Excel). Vượt quá 31 ký tự khiến Excel báo lỗi "We found a problem with some content..." khi mở file. Đặt tên ngắn gọn (vd: `1. TTH Ban Nhieu`, `2. So Sanh 3 Ben (TTH-Dor-CFB)`).
  - **Cấu trúc cột liền kề theo từng nhóm thông tin**: Xếp các cột cùng chiều dữ liệu của 3 bên cạnh nhau để so sánh trực quan:
    `STT | Nhóm Hàng | Tên Tuitehao | Tên Doravo | Tên CloneFBIG | Giá Tuitehao | Giá Doravo | Giá CloneFBIG | Stock Tuitehao | Stock Doravo | Stock CloneFBIG | Đã Bán Tuitehao | Đã Bán Doravo | So Sánh Bán | Tình Trạng Doravo | Link Tuitehao | Link Doravo | Link CloneFBIG`
  - **Tên cột rõ ràng**: Ghi rõ `Stock CloneFBIG`, `Giá CloneFBIG`, không dùng từ chung chung như "Nguồn" gây khó hiểu.
  - **Giá quy đổi đồng nhất**: Luôn thể hiện cả VNĐ và USD: `VNĐ ($USD) [Tệ]` (tỷ giá: 1 CNY ≈ 3.500đ, 1 USD ≈ 26.500đ).
  - **Quy tắc cột 'So Sánh Bán' (Đánh giá lệch nguồn)**:
    - Hàng up tay (`supplier_id=0`): ĐỂ TRỐNG hoặc `—` (không so sánh số bán).
    - Hàng bên mình bán nhiều hơn hoặc xấp xỉ đối thủ: ĐỂ TRỐNG hoặc `—` (không cần flag).
    - CHỈ đánh dấu **`Bị lệch`** (tô màu cam nhạt) khi đối thủ bán nhiều vượt trội trên sản phẩm API chung kho mà bên mình = 0 / rất ít.
    - Trong ô chỉ ghi ngắn gọn nhãn `Bị lệch` hoặc `—`, TUYỆT ĐỐI KHÔNG viết câu giải thích dài dòng trong ô dữ liệu. Đặt câu hướng dẫn đọc (chữ đỏ nổi bật) ở các dòng ghi chú trên đầu sheet (Row 2–3).
  - **Điền link đầy đủ**: Điền link cho cả hàng đang ẩn / hết hàng (kèm ghi chú `(Ẩn do hết hàng)`).
  - **Thẩm định dữ liệu độc lập (Plan-Review)**: Khi cần kiểm tra chéo độ chính xác của bảng Excel đối chiếu, gọi model `plan-review` qua 9Router HTTP (`POST /v1/chat/completions`, `tools: []`, `tool_choice: "none"`, timeout ≥ 180s) để rà soát khách quan tỷ giá, khớp stock và tính thuần túy dữ liệu trước khi xuất bản.

## References

- `references/tiktok-market-accounts-pricing-2026.md` — bảng giá thị trường thực tế các loại acc TikTok (Giỏ hàng 0 follow vs 1k Follow vs Full Combo Live + Giỏ hàng) kèm link khảo sát thực tế (MuaCash, ShopGiangMedia, Taikhoanre) & kỹ thuật fallback tìm kiếm Cốc Cốc qua browser.
- `references/tuitehao-cc.md` — dữ liệu chi tiết tuitehao.cc (danh mục, giá, chính sách) đã thu thập 2026-08.
- `references/tuitehao-vs-trustvia-accsmtp-audit-2026-08.md` — báo cáo đối chiếu tuitehao vs (trustvia.net, accsmtp.com) & vs 2 nguồn user (clonefbig, taikhoan295) ngày 2026-08-16: bằng chứng loại trừ trustvia/accsmtp + bằng chứng trùng 100% clonefbig + loại trừ taikhoan295.
