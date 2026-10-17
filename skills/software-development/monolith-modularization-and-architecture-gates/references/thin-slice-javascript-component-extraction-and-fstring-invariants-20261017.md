# Thin-Slice JavaScript Component Extraction from Python F-String Monoliths (2026-10-17)

## 1. Bối cảnh & Cạm Bẫy Trần Diff 30KB (`tiktok_dashboard.py`)
Khi phân rã các dashboard web nguyên khối viết bằng Python (`tiktok_dashboard.py` ban đầu 3.437 dòng):
- Khối giao diện frontend chứa ~1.570 dòng JavaScript (~104 KB) được nhúng trực tiếp trong chuỗi `html = f"""..."""`.
- **Cạm bẫy Big-Bang:** Nếu cắt toàn bộ 104 KB JavaScript sang file ngoài trong 1 commit duy nhất, dung lượng git diff sẽ đạt ~150-200 KB, vi phạm quy chuẩn `MAX_DIFF_BYTES_GATE = 30_000` của Closeout Gate và bị hệ thống ngắt cầu dao (Fail-Fast) lập tức.

## 2. Chiến Lược Phân Rã Lát Cắt Mỏng (Thin-Slice Decomposition)
Thay vì trích xuất toàn bộ JavaScript trong một lần, chia nhỏ theo từng miền chức năng độc lập vào thư mục `dashboard/static/`:
1. **Lát 1 (Account History Modal):** Trích xuất `dashboard/static/history_modal.js` (273 dòng, 14.182 bytes diff) gồm logic Modal lịch sử nick, sparklines SVG (`drawSparklineSvg`), và biểu đồ SVG tương tác (`drawSvgChart`, `showTooltip`).
2. **Lát 2 (Farm History Modal):** Trích xuất `dashboard/static/farm_history.js` (~220 dòng, ~14 KB diff) gồm Modal lịch sử toàn farm, biểu đồ tăng trưởng và tooltip farm.
3. **Lát 3 (Table & KPI Rendering):** Trích xuất `dashboard/static/table.js` (~420 dòng, ~25 KB diff) gồm logic `renderTable`, nhãn cụm máy `mayTagHtml`, định dạng `deltaBadgeHtml`, và sắp xếp bảng.
4. **Lát 4 (Bootstrap & Event Listeners):** Trích xuất `dashboard/static/app.js` (~300 dòng, ~18 KB diff) gồm bộ đếm KPI, lắng nghe sự kiện filter, và polling auto-refresh 30s.

Mỗi lát cắt đều có diff $\le 25.000$ bytes, vượt qua Closeout Gate dễ dàng với điểm số $\ge 90/100$.

## 3. Quy Tắc Khử Ngoặc Nhọn Kép (`{{` $\to$ `{`) & F-String Injection
1. **Khử ngoặc nhọn kép:** Trong file JavaScript độc lập (`.js`), toàn bộ các dấu `{{` và `}}` dùng để thoát f-string Python bắt buộc phải hoàn nguyên về `{` và `}` đơn chuẩn của JavaScript:
   ```python
   raw_js = "".join(lines[start:end])
   clean_js = raw_js.replace("{{", "{").replace("}}", "}")
   ```
2. **Kiểm tra cú pháp JavaScript độc lập:** Chạy `node --check dashboard/static/<file>.js` để đảm bảo file JS không có lỗi cú pháp trước khi tích hợp.
3. **Nạp & Chèn Động (Dynamic Inlined Injection):**
   Trong file Python chính:
   ```python
   _HISTORY_MODAL_JS_PATH = pathlib.Path(__file__).resolve().parent / "dashboard" / "static" / "history_modal.js"
   _HISTORY_MODAL_JS = _HISTORY_MODAL_JS_PATH.read_text(encoding="utf-8") if _HISTORY_MODAL_JS_PATH.exists() else ""
   ```
   Và chèn trực tiếp biến `{_HISTORY_MODAL_JS}` vào chuỗi HTML f-string.
   *Nguyên lý:* Python thực hiện thay thế nguyên văn chuỗi (verbatim substitution) mà không biên dịch lại các dấu `{` hay `}` đơn bên trong mã JS, giúp giữ trọn vẹn 100% tính tương thích ngược với mọi bộ test hiện có (91/91 tests pass).

## 4. Kiểm Thử Thẩm Định Độc Lập Qua Claude Sonnet 5.5
Mỗi commit lát cắt JavaScript bắt buộc được Claude Sonnet 5.5 (`--role reviewer`) thẩm định độc lập:
- Đối chiếu dòng xóa khỏi Python và dòng thêm vào file JS sau khi unescape khớp 100%.
- Xác nhận không có biến `{var}` Python nào bị thất thoát hoặc giải mã sai.
- Chạy toàn bộ unit test suite để xác nhận không gây hồi quy hành vi.
