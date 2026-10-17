# Bóc Tách Frontend JavaScript Monolith F-String Dưới Trần Diff 30KB & Kiến Trúc Hybrid WinRT OCR vs XML Dump (17/10/2026)

## 1. Thách thức: 104KB Inlined JavaScript trong Python F-String (`tiktok_dashboard.py`)

Trong các dashboard Python nguyên khối như `tiktok_dashboard.py` (2.146 dòng):
- Phần mã JavaScript giao diện (quản lý bảng, bộ lọc, modal lịch sử tài khoản, modal tăng trưởng farm, biểu đồ SVG sparklines) chiếm tới **1.569 dòng** (~104.664 bytes).
- **Cạm bẫy trần Diff của Closeout Gate (`MAX_DIFF_BYTES_GATE = 30_000` bytes):**
  Nếu trích xuất toàn bộ khối JavaScript này ra file `dashboard/static/app.js` trong một commit duy nhất, git diff sẽ đạt > 140.000 bytes (gấp 4.6 lần trần cho phép), khiến `closeout_gate.py` lập tức ngắt cầu dao với lỗi:
  `[Gate Fail-Fast: DIFF_TOO_LARGE] targeted diff quá lớn (> 30000 bytes). Vi phạm quy chuẩn phân rã task O(1).`

---

## 2. Giải Pháp: Phân Rã Thin-Slices Theo Miền Chức Năng (Domain-Based Extraction)

Thay vì cắt toàn bộ trong một lượt (Big-Bang), ta chia nhỏ khối JavaScript thành 4 lát cắt độc lập theo miền logic vào thư mục `dashboard/static/`, mỗi commit diff đều đảm bảo $\le 25.000$ bytes (< trần 30KB):

### Lát cắt 1: Account History Modal & Sparklines (`dashboard/static/history_modal.js` ~24KB)
- Chứa các hàm: `openHistoryModal`, `closeHistoryModal`, `switchMetric`, `drawSparklineSvg`, `drawSvgChart`, `showTooltip`.
- Tách riêng logic modal tra cứu lịch sử chi tiết từng tài khoản.

### Lát cắt 2: Farm Growth History Modal & Charts (`dashboard/static/farm_history.js` ~22KB)
- Chứa các hàm: `openFarmHistoryModal`, `closeFarmHistoryModal`, `switchFarmMetric`, `drawFarmChartSvg`, `renderFarmOverview`, `showFarmTooltip`.
- Tách riêng modal xem biểu đồ tăng trưởng toàn farm.

### Lát cắt 3: Table Rendering & Machine Cluster Badges (`dashboard/static/table.js` ~26KB)
- Chứa các hàm: `renderTable`, `mayTagHtml`, `deltaBadgeHtml`, `rankLabel`, `sortTable`, `updateKpiDelta`.
- Quản lý logic hiển thị bảng danh sách tài khoản chính.

### Lát cắt 4: Core Bootstrap & Event Polling (`dashboard/static/app.js` ~15KB)
- Chứa logic khởi tạo, lọc tìm kiếm (`filterTable`), auto-refresh 15s (`pollDashboardUpdates`).
- Đưa file chính `tiktok_dashboard.py` về mỏng dưới 250 dòng chuẩn kiến trúc thin-entrypoint.

---

## 3. Kỹ Thuật Chuyển Đổi Ký Tự F-String Sang JavaScript Thuần Túy

Khi chuyển mã JavaScript từ Python f-string ra file `.js` tĩnh:
1. **Chuyển đổi dấu ngoặc nhọn kép:** 
   Trong f-string, mọi dấu `{` và `}` đều phải viết kép `{{` và `}}`. Khi đưa ra file `.js`, bắt buộc thay thế về `{` và `}` đơn (ví dụ: `function foo() { ... }`).
2. **Cô lập biến Python Server-Side Injection:**
   Các biến do Python render vào như `const initialData = {initial_json};` cần được giữ ở một thẻ `<script>` inline nhỏ trên file HTML chính hoặc qua data-attribute, KHÔNG nhồi cứng vào file `.js` tĩnh để tránh lỗi cú pháp JS:
   ```html
   <script>
       window.__DASHBOARD_INITIAL_DATA__ = {initial_json};
   </script>
   <script src="/static/app.js" defer></script>
   ```

---

## 4. Kiến Trúc Hybrid: WinRT OCR (Primary) vs XML Dump (Fallback)

### Đánh giá từ Chuyên gia Kiến trúc (Claude Sonnet 5.5):
1. **Tại sao WinRT OCR (`automation_core.ocr`) làm PRIMARY là tối ưu:**
   - **Tốc độ:** Chụp frame màn hình và OCR trên Windows CPU chỉ mất **0.2s - 0.4s**, trong khi `uiautomator dump` mất **1.5s - 3.5s**.
   - **Triệt tiêu lỗi sập Android S7:** Trên các dòng máy cũ (Android 7), daemon uiautomator thường xuyên bị kernel gửi tín hiệu `Killed (EXIT=137)` do tràn RAM.
   - **Xử lý bề mặt mù XML:** TikTok sử dụng ngày càng nhiều giao diện Flutter, WebView, và custom canvas nơi cây XML trả về `null root node`.
2. **Vai trò của XML Dump làm FALLBACK:**
   - Khi cần kiểm tra các thuộc tính cấu trúc sâu: `resource-id`, `clickable=true`, `bounds` tuyệt đối, hoặc khi màn hình không có chữ rõ ràng.
3. **Các bẫy farm bắt buộc phòng vệ:**
   - **Bẫy text dài (Bio/Mô tả):** Khi tìm nút bấm bằng từ khóa ngắn (như "Follow" hay "Đóng"), nếu Bio chứa chữ này sẽ click nhầm. Bắt buộc chặn độ dài: `len(n_txt.split()) <= 3`.
   - **Bẫy Tab Bar đỉnh màn hình ($y < 200$):** Chữ "Bạn bè", "LIVE" ở thanh điều hướng trên cùng dễ bị nhận nhầm thành trạng thái quan hệ. Luôn áp dụng `y_min >= 200`.
   - **Bẫy Optimistic UI & Follow Dominance:** Khi app TikTok hiển thị đồng thời cả nút Follow và Nhắn tin, luôn ưu tiên trạng thái chưa follow nếu còn xuất hiện từ khóa follow.
   - **Không nuốt exception âm thầm:** Mọi lượt OCR thất bại bắt buộc ghi log có cấu trúc `[OCR_TELEMETRY]` để phục vụ giám sát và đo lường độ tin cậy.
