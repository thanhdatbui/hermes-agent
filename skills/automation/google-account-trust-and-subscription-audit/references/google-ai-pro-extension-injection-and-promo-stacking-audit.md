# Phân Tích & Đối Soát Extension Bơm Offer Google AI Pro (TUT Stacking Promo Token)

## 1. Nguồn Gốc & Danh Tính Kỹ Thuật
- **Tên tiện ích:** `Xi · Google AI Pro 2Y Offer Injector` (bản tiếng Trung, xuất phát từ channel `t.me/pk_oa`).
- **Tên file phân phối:** `google_pro_6_12_24.zip` (ID Drive thường gặp: `1TKIJOi8uCh0GVig9rHrZVogk0y_wQ1hZ`).
- **Thành phần:** Gồm `manifest.json` (MV3), `content.js`, `inject.js`, `play_guard.js`, `popup.html`, `popup.js`, icon assets. Không có file nhị phân (`.exe`, `.dll`) hay script shell.

## 2. Cơ Chế Hoạt Động Kỹ Thuật (Under The Hood)
- **Host Permissions:** Chỉ khai báo `https://one.google.com/*`, `https://tokenized.play.google.com/*`, `https://play.google.com/*`. Không có quyền `<all_urls>` hay `nativeMessaging`.
- **Kỹ thuật can thiệp (Tamper / Hook):**
  - Chạy `inject.js` ở ngữ cảnh `MAIN` world tại `one.google.com`.
  - Hook vào `XMLHttpRequest.prototype.send`, bắt các payload RPC `Ngbm` và URL `/eacquire/multiline`.
  - Thay thế danh mục sản phẩm thanh toán `full_items` thành token khuyến mãi: `subs:com.google.android.apps.subscriptions.red:g1.2tb.ai.subs_variant` đi kèm mảng các promo offer token hardcoded:
    * `12m`: Offer 12 tháng.
    * `6m_ss`: Offer 6 tháng (Samsung/Pixel bundle).
    * `6m`, `6m_2`: Offer 6 tháng bổ trợ / dự phòng.
    * Kèm theo token add-on YouTube Premium miễn phí: `g1.youtube_premium_individual_add_on`.
  - Giao diện `play_guard.js` quét DOM iframe của Google Play: phát hiện chữ "free trial / $0.00 / 免费试用" thì hiện banner xanh, phát hiện "charged today / pay now" thì hiện banner đỏ cảnh báo.

## 3. Đánh Giá Rủi Ro Thực Tế
- **Về tính độc hại trên PC/Host:** Không có backdoor, trojan hay stealer gửi cookie/thẻ ngân hàng ra máy chủ ngoài (thuần client-side RPC payload modification).
- **Về tài khoản & thanh toán (P0 Risk):**
  - **Trừ tiền thật:** Khi Google đóng pool offer token hoặc tài khoản/IP không thỏa mãn điều kiện promo, checkout Google Play sẽ fallback trừ theo giá niêm yết hàng tháng.
  - **Khóa cổng thanh toán & Ban tài khoản:** Google Payments quét bất thường (Tamper RPC `Ngbm`, stack nhiều chu kỳ promo tới 2028), dẫn tới khóa hồ sơ Google Pay (`OR-CCSEH`, `OR-PMSA`) và cấm thanh toán vĩnh viễn trên acc đó.
  - **Bẫy hủy gia hạn:** Hủy sớm trên Google Play với một số offer trial có thể khiến Google thu hồi ngay quyền lợi thay vì bảo lưu thời hạn.

## 4. Quy Chuẩn Nạp Vào GPM Profile Khi Cần Thử Nghiệm Cô Lập
- **Tuyệt đối cấm:** Cài vào Chrome chính của máy host hoặc profile GPM chứa Gmail chính/tài khoản công việc/tài khoản liên kết farm.
- **Quy trình nạp cô lập trên GPM:**
  1. Giải nén vào thư mục cố định riêng biệt (ví dụ `D:/tools/gapt_injector`).
  2. Dùng profile GPM rác gắn sẵn Proxy US Residential sạch.
  3. Mở profile -> `chrome://extensions` -> Bật `Developer mode` -> `Load unpacked` (hoặc truyền qua cờ CLI `--load-extension="D:\tools\gapt_injector"`).
