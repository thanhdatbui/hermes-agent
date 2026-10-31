# Shopee & Marketplace Research Automation Pitfalls & Guidelines

## 1. Bẫy giá Clickbait Phân loại hàng (Variant Traps)
- **Cơ chế clickbait của sàn TMĐT (Shopee, Lazada):**
  - Giá hiển thị trên banner tìm kiếm hoặc danh sách kết quả (`search_items`) LUÔN là giá chặn dưới của phân loại rẻ nhất (`price_min`).
  - Đối với thiết bị phần cứng (Mini PC, Soft Router, Server, linh kiện máy tính), giá rẻ nhất hầu như 100% là:
    1. **`Barebone` (Xác máy):** Chỉ có vỏ case + mainboard + nguồn; hoàn toàn **CHƯA CÓ CPU, RAM, SSD**.
    2. **Option CPU đời cổ nhất / thấp nhất:** Ví dụ chip Celeron đời Tống (J1900, G4400) trong khi tiêu đề giật tít "Core i5 / i7 / N100".
- **Kỷ luật bắt buộc khi tư vấn giá cho User:**
  - **CẤM TUYỆT ĐỐI** báo giá dựa trên số liệu hiển thị ngoài trang tìm kiếm hoặc API `price_min`.
  - BẮT BUỘC phải mở trang chi tiết sản phẩm, click chọn đủ các biến thể thực tế (CPU/Model + RAM/SSD) để đọc mức giá thật trước khi gửi link hoặc tư vấn chi phí.
  - Khi gửi link sản phẩm cho User: Bắt buộc nêu rõ link kèm cấu hình cụ thể tương ứng với mức giá đó (VD: "Bản Full RAM 8GB + SSD 128GB giá 2.7tr", tránh chỉ quăng link cụt ngủn khiến User bấm vào thấy giá khác).

## 2. Browser Automation & Anti-Bot Quirks
- **Shopee Anti-Crawl (403 Forbidden / Login Required):**
  - Chạy Playwright headless mới toanh hoặc `curl` trực tiếp vào API `shopee.vn/api/v4/...` sẽ bị chặn `403 Forbidden` hoặc chuyển hướng sang trang `Login Required`.
  - **Giải pháp:** Tương tác trực tiếp trên cửa sổ Chrome chính đã đăng nhập sẵn của User (`Profile 4 / jinrakal`) qua `computer_use` (SOM click / set_value) hoặc CDP port 9222.
- **Chrome Omnibox Navigation Quirk:**
  - Khi đổi trang trên Chrome thông qua `computer_use`, dùng `action='set_value'` trên thanh địa chỉ (Omnibox) rồi click vào gợi ý dropdown của Omnibox, hoặc click vào nút Reload / link trong trang để tải lại nội dung mượt mà.
