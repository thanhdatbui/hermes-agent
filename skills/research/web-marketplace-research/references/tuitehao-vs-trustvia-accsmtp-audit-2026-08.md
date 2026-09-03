# Tuitehao vs Trustvia & Accsmtp vs CloneFBIG & Taikhoan295 (Audit 2026-08-18)

## 1. Kết luận chính

- **tuitehao KHÔNG lấy hàng từ trustvia.net hay accsmtp.com.** Format đặt tên, đuôi mail, chủng loại và quy mô stock hoàn toàn khác biệt.
- **tuitehao LẤY TRỰC TIẾP TỪ clonefbig.com (cùng kho 100%).** Toàn bộ dòng FB TempMail/Smvmail/Fvia và dòng IG Clone No-Email của tuitehao khớp realtime từng con stock với clonefbig.
- **tuitehao KHÔNG lấy từ taikhoan295.com.** TikTok của tuitehao lấy từ kho TQ nội địa riêng quy mô lớn hơn nhiều (50k+ acc 2025).

---

## 2. Chi tiết đối chiếu tuitehao vs trustvia.net & accsmtp.com

### trustvia.net
- Site CMSNT đóng cổng toàn bộ sau login (kể cả catalog sản phẩm và tài liệu API tại `/document-api`).
- **Đã quét 8 danh mục từ source:** TIKTOK VIỆT, TIKTOK NGOẠI, TikTok Live Studio - Seller, TikTok Ads + BC TikTok, HOTMAIL OUTLOOK, Proxy IPV4, Proxy Xoay IPv6, VPN License key.
- **Hoàn toàn KHÔNG có:** Facebook, Instagram, Twitter/X, hay Telegram. Quy mô tuitehao là chợ acc lẻ hàng chục ngàn tồn kho (Twitter/FB/IG/TG) — không liên quan tới dịch vụ proxy/tool/TikTok VN của trustvia.

### accsmtp.com
Dump toàn bộ bảng sản phẩm public qua browser DOM (các tab Facebook new/old/friends, Twitter(X), Instagram, Gmail, TikTok, Hotmail):

| Mặt hàng | accsmtp.com | tuitehao.cc | So sánh |
|---|---|---|---|
| **Facebook** | Toàn bộ gắn đuôi domain **`fviainboxes.com`**, Microsoft Hotmail, UID kèm token/cookie | Rất nhiều sp ghi rõ **`TempMail.Plus`**, **`Smvmail`**, **`Fvia`**, **`Mailclone.site`**, UID **`6157x`** | **Khác nguồn**: tuitehao dùng dòng TempMail/Smvmail (trùng 100% clonefbig), accsmtp dùng dòng riêng fviainboxes format khác |
| **Instagram** | Dòng **`firstmail.ltd`** (50-1000 followers, $1.43–$5.00), **`moakt.com`**, **`besttemporaryemail.com`**, stock vài chục tới 1.8k | Dòng **`no-email` (无邮箱)**, **`SMS API`**, **`temp-mail.io`**, stock **130.000+**, giá ¥1.1–1.5 | **Khác nguồn**: accsmtp chuyên IG có follower/mail riêng, tuitehao bán IG clone không mail stock khổng lồ (trùng clonefbig) |
| **Twitter / X** | Chủ yếu **acc có follower 10k-20k** ($52.50–$105.00) hoặc old 2009-2024 (hầu hết out of stock) | Chủ yếu **X new reg Outlook 2FA** (¥0.8–1.8, stock hàng chục nghìn, bán chạy 46k–50k) | **Khác nguồn**: accsmtp không có dòng X new rẻ như tuitehao |
| **TikTok** | Acc country theo format: `Hotmail live OAUTH2 / Mail Die`, tồn kho vài trăm – 4k (Peru 3.524, VN 1.616, FR 1.414, $0.07–$0.14) | TikTok lão 2025 (¥8, tồn 53.5k), TikTok 白号 random IP (¥1–1.5, tồn 35k), UK/FR/DE | **Khác format & quy mô**: tuitehao bán TikTok new/old TQ số lượng lớn, accsmtp bán acc mail die/oauth lẻ |
| **Hotmail** | Hotmail Graph API $0.01 (stock 40k), OAuth2 $0.01 (stock 35k) | Không bán Hotmail lẻ (chỉ kèm trong acc) | — |

---

## 3. Bảng đối chiếu tuitehao.cc ↔ clonefbig.com ↔ doravo.net (Live 2026-08-18)

| SP CloneFBIG (API ID) | Tên sản phẩm | Giá nguồn | Stock nguồn | tuitehao.cc (Giá / Stock) | Link tuitehao | Doravo.net (ID / Giá) | Link Doravo |
|---|---|---|---|---|---|---|---|
| **16** | IG Clone 2FA On Aged 1–30 | 2.000đ ($0.077) | 131.268 | ¥1.42 (Stock 0 - tắt bán) | `item?id=1380` | ID 56 (3.710đ = $0.14) | `instagram-clone-random-username-phone-registered-live-verified-phone-or-email-2fa-on-aged-130-days-2fa-on16` |
| **3591** | IG Clone No 2FA Aged 1–30 | 1.800đ ($0.068) | 0 (hết) | ¥1.20 (Stock 0 - hết) | `item?id=1379` | ID 67 (3.240đ = $0.12 - tự ẩn) | `instagram-clone-random-username-phone-registered-live-verified-phone-or-email-no-2fa-aged-130-days3591` |
| **5** | IG 1–3M Aged 282 US Name 2FA | 6.000đ | 3.025 | ¥6.20 (Stock 3.026 - khớp 100%) | `item?id=1291` | ID 9 (12.000đ = $0.45) | `instagram-clone-us-name-phone-registered-13-months-aged-282-unlocked-verified-via-temp-mailio-2fa-on-100-fresh5` |
| **18** | FB No 2FA 1–7 Ngày TempMail | 3.000đ | 37.643 | ¥2.18 (Stock 37.643+) | `category/facebook-new-account.html` | ID 6 (6.000đ = $0.23) | `facebook-clone-name-global---android-registration---add-tempmailplus-to-receive-code---no-2fa---valid-for-1-30-days18` |
| **3187** | FB 2FA 30–180 Ngày TempMail/Smvmail | 5.500đ | 13.568 | ¥5.70 (Stock 13.569 - khớp 100%) | `category/facebook-new-account.html` | ID 4 (11.000đ = $0.42) | `facebook-clone-name-global---android-registration---add-tempmailplus---smvmail---fvia-to-receive-code---the-account-was-created-30-180-days3187` |
| **3562** | FB 2025 UID 6157x Fvia/Mailclone | 7.200đ | 762 | ¥5.13–7.46 (Stock 766 - khớp) | `item?id=1316` | ID 5 (14.400đ = $0.54) | `facebook-clone-name-global-2025---uid-6157x---android-registration---add-fviainboxescom---mailclonesite-to-receive-code---valid-for-6-month-2-year3562` |
| **3470** | Hotmail Graph API Live 6–12M | 270đ | 18.728 | Không bán lẻ (kèm acc) | — | ID 12 (540đ = $0.02) | `hotmail-trusted-graph-api-format-live-612-months-recovery-mail-added-fviainboxescom-read-description-carefully3470` |

---

## 4. Các mặt hàng tuitehao có mà doravo / clonefbig chưa có (nguồn riêng TQ)
1. **Twitter / X New Reg 2FA Outlook (CT0 / Auth Token)**: ¥0.8 – ¥1.1 (2.8k–3.8k), đã bán 50k+, stock sẵn 2k-3k.
2. **Telegram API接码 (+57, +95, +1)**: ¥6 – ¥9.98, stock 17k+.
3. **Facebook & Instagram Old 2012–2020**: ¥30 – ¥80 (105k–280k) kèm follow thật.
4. **TikTok Lão 2025 (53.5k) & TikTok 白号 (35k)**: quy mô lớn nội địa TQ.
