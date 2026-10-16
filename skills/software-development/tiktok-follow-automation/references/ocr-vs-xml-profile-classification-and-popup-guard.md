# OCR vs XML Profile Classification & Popup Guard Patterns

## 1. Bản chất sự khác biệt: XML vs WinRT OCR
- **XML (uiautomator / atx-agent):**
  - *Ưu điểm:* Đọc chính xác tuyệt đối text gốc từ bộ nhớ Android (không bị méo ký tự `@username`, UID). Đọc được các thuộc tính trạng thái: `selected="true"`, `checked="true"`, `focused="true"`, `password="true"`.
  - *Nhược điểm:* Chậm (3s - 15s/lần dump, dễ timeout). Bị gãy khi TikTok cập nhật đổi mã `resource-id` (`id/fds` -> `id/ff8` -> `id/fmp` -> `id/fo4`).
- **WinRT OCR (native CPU 0.3s):**
  - *Ưu điểm:* Siêu tốc (0.2s - 0.5s/lần cả chụp + đọc). Hoàn toàn miễn nhiễm với việc TikTok đổi `resource-id`. Cho tọa độ tâm $(cx, cy)$ chính xác để tap trực tiếp.
  - *Nhược điểm:* Thị giác phẳng (flat vision). Không phân biệt được text nút bấm với text Bio, nhãn thống kê (stat counter) nếu không có bộ lọc tọa độ và từ khóa. Dễ đọc nhầm ký tự tương tự (`0` vs `O`, `l` vs `1`).

## 2. Chiến lược Hybrid (Lai ghép chuẩn xác)
- **Nhóm Action Button (Follow / Đăng ký / Tiếp tục):** Ưu tiên XML -> nếu `unknown` do đổi ID thì Fallback sang OCR ngay để cứu nguy, không để script bị timeout/crash.
- **Nhóm Dập Popup đè màn hình ("Để sau", "Không phải bây giờ", "Hủy", "Đóng"):** Đưa OCR làm First-Line (0.3s). Quét nhanh thấy nút đóng là tap dập tắt ngay, không tốn 10s dump XML làm đơ nhịp lướt video.
- **Nhóm Định danh (@username / UID) & Thuộc tính trạng thái:** BẮT BUỘC dùng XML 100%. Tuyệt đối không dùng OCR đọc username để đối soát Excel hay kiểm tra tab `selected="true"`.

## 3. Quy tắc Follow Dominance trên Profile TikTok
Khi tài khoản chưa follow (hoặc bị nhả follow):
- Nếu nick mở DM công khai hoặc họ đã follow mình trước: Profile hiển thị **CẶP NÚT SONG SONG**:
  - Nút 1: `[Follow]` hoặc `[Follow lại]` (màu đỏ)
  - Nút 2: `[Nhắn tin]` (màu xám)
- **Luật Follow Dominance:**
  - Chỉ cần xuất hiện từ khóa chưa follow (`"follow"`, `"follow lại"`, `"theo dõi"`) trong dải action ($y < 1200$) -> **LUÔN LUÔN KẾT LUẬN LÀ `not_followed`**, bất kể có nút "Nhắn tin" bên cạnh hay không.
  - Chữ "Nhắn tin" chỉ được tính là `followed` khi KHÔNG CÒN bất kỳ nút follow đỏ nào trên header.

## 4. Các bẫy substring & nhãn đếm (Stat Counters)
- **Bẫy Substring:**
  - `"follower"`, `"followers"`, `"dang follow"`, `"da follow"` đều chứa từ `"follow"`. Nếu dùng `kw in text` sẽ nhận nhầm cột follower thành nút follow!
  - `"dang theo doi"` (đang theo dõi - Following) chứa từ `"theo doi"` (theo dõi - Follow). Nếu match `"theo doi"` mà không loại trừ `"dang theo doi"` sẽ phân loại ngược từ followed thành not_followed!
- **Bẫy Stat Counter:**
  - Cột đếm số lượng: `127 Đã follow`, `10K Follower`, `0 Đang follow`. Bắt buộc dùng regex loại trừ triệt để các nhãn đếm này trước khi kiểm tra nút bấm.
