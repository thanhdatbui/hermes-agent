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

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
