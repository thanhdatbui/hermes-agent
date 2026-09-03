# In-Feed Friend Follow Suggestion Card & Popup Handling (Case 50)

## 1. Hiện tượng & Bản chất UI
Trên luồng lướt Feed TikTok, thuật toán thường xuyên chèn các thẻ/popup đề xuất bạn bè in-feed dạng ViewPager/Card:
- Tiêu đề / Nhãn quan hệ: `"Follow bạn"`, `"Bạn bè với"`, `"Gợi ý follow"`, `"Follow bạn bè của bạn"`, `"Người bạn có thể biết"`.
- Nút tương tác chính: `"Follow lại"` (`com.ss.android.ugc.trill:id/c3l`), `"Follow back"`, `"Theo dõi lại"`.
- Nút phụ: `"Không quan tâm"` (`com.ss.android.ugc.trill:id/c3m`), `"Vuốt lên để bỏ qua"`.
- Nút đóng: Icon $X$ (`com.ss.android.ugc.trill:id/c3t`, `id/e63`, hoặc content-desc `"Đóng"`).

## 2. Các Anti-Pattern thường gặp
1. **Thiếu import helper trong module popup:**
   - Khi gọi `capture_required_ui` trong `flows/benign_popup.py` nhưng quên import từ `core.ui_capture`, Python văng `NameError`. Bẫy `except Exception` nuốt lỗi và trả `initial_capture_failed` $\rightarrow$ không bấm được nút.
2. **Khớp tiêu đề cứng (Rigid semantic matching):**
   - Chỉ tìm chính xác chuỗi `"Follow bạn bè của bạn"`, bỏ lọt các biến thể ngắn hơn như `"Follow bạn"`, `"Bạn bè với"`.
3. **Bắt nhầm node bị tràn mép màn hình (Offscreen / Boundary-clipped nodes):**
   - Do ViewPager chứa các card liền kề nhau, node $X$ (`c3t`) của card bên trái nằm ở tọa độ mép $[0, 462][46, 570]$ (chiều rộng chỉ 46px). Nếu bộ quét DOM lấy phần tử đầu tiên mà không lọc tọa độ, script sẽ tap vào $x=23$ (ngoài vùng hiển thị của nút thật ở $x=864$), làm việc đóng thẻ thất bại và kích hoạt `unexpected popup/dialog marker detected`.

## 3. Quy tắc xử lý chuẩn (Case Fix)
1. **Import đầy đủ:**
   - Luôn import `from core.ui_capture import capture_required_ui` tại đầu `flows/benign_popup.py`.
2. **Lọc tọa độ bounds an toàn:**
   - Nút tap `"Follow lại"`: Bắt buộc $x \ge 50$ và $y > 300$.
   - Nút đóng $X$ hoặc `"Không quan tâm"`: Loại bỏ các node có $x < 50$ hoặc $\text{width} < 30\text{px}$.
3. **Trình tự tương tác:**
   - Bấm nút `"Follow lại"` trước $\rightarrow$ `followed_count += 1`.
   - Chờ UI cập nhật và recapture hierarchy tươi qua `capture_required_ui`.
   - Tìm nút đóng $X$ hợp lệ hoặc nút `"Không quan tâm"` để đóng card sạch sẽ $\rightarrow$ đưa màn hình về trạng thái Feed For You bình thường.
