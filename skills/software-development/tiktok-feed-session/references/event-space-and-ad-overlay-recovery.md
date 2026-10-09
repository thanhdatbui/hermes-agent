# Event Space ("Không gian sự kiện") & In-Feed Ad Overlay Recovery

## 1. Phân biệt In-Feed Ad Overlay vs Màn hình "Không gian sự kiện"

Khi TikTok hiển thị quảng cáo hoặc sự kiện, flow `benign_popup.py` cần phân biệt rõ 2 loại:

### A. In-Feed Ad Overlay (`sponsored-ad-feedback` / CTA "Mua ngay")
- **Đặc điểm:** Nằm đè trực tiếp lên video quảng cáo trong Feed chính (For You / Following). Có câu hỏi khảo sát "Bạn có quan tâm đến quảng cáo này không?" hoặc nút CTA mua hàng kèm nút Đóng không có tác dụng.
- **Cơ chế thoát:** Bounded swipe up (`_dismiss_feed_ad_overlay_by_swipe`). Vuốt sang video tiếp theo sẽ tự động thoát overlay ad.

### B. Màn hình "Không gian sự kiện" (Live Event Space / MegaLive Catalog)
- **Đặc điểm:** Là một sub-view/web-view độc lập được kích hoạt từ feed hoặc banner.
  - Top bar có tiêu đề: `"Không gian sự kiện"` (kèm biến thể UTF-8/mojibake).
  - Nút Back mũi tên (`←`) ở góc trên bên trái.
  - Nội dung là danh sách các card sự kiện LIVE ("MEGALIVE MỸ PHẨM...", "SIÊU SALE NGÀY ĐÔI...", "SỰ KIỆN LIVE MỞ BÁN...") kèm nút "Đăng ký".
- **Lỗi thường gặp:**
  - Script classifier nhận diện nhầm thành `manual-needed:sponsored-ad-feedback`.
  - Handler thử dùng swipe để skip: thao tác swipe up chỉ cuộn danh sách card sự kiện bên trong trang, KHÔNG THOÁT ĐƯỢC MÀN HÌNH.
- **Cơ chế thoát chuẩn:**
  - BẮT BUỘC xử lý bằng `action="press_back"` (gửi KeyEvent `BACK` / keycode 4) hoặc tap nút Back arrow trên Top bar.
  - Sau khi press BACK, thực hiện recapture để xác minh TikTok đã quay lại Feed chính (`for-you` / `following`).

---

## 2. Quy tắc Điều tra Hiện trường (Tránh Timeout 900s)

- **CẤM TUYỆT ĐỐI:** Dùng `glob.glob('**', recursive=True)` quét nội dung toàn bộ file `.xml`, `.txt`, `.json` trong `.ai-runs`. Thư mục `.ai-runs` chứa hàng trăm batch run và hàng chục nghìn file XML/PNG capture, script quét đĩa sẽ bị **timeout (900s)** làm treo session và cạn tool budget.
- **Cách tra cứu đúng:**
  1. Nếu user đã cung cấp thông tin alert (máy, serial, text hiện trường): Sử dụng ngay thông tin đó làm ground truth để vào thẳng code flow (`benign_popup.py`, `classifier.py`).
  2. Để xem summary của máy cụ thể: Chỉ inspect trực tiếp run folder gần nhất theo ngày (`.ai-runs/YYYYMMDD-*/machines/machine_<N>/summary.txt`) hoặc đọc file canary run riêng lẻ.
