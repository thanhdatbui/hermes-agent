# Multimodal Vision Document Translation & Review Pattern

## Bối cảnh
Khi xử lý tài liệu scanned phức tạp (như catalogue thiết bị PCCC, catalogue kỹ thuật công nghiệp có nhiều bảng thông số, sơ đồ, chữ Hán hoặc chữ nhỏ) bằng mô hình Vision LLM (Gemini 3.8 / Flash / Claude Vision):
- File PDF gốc dạng ảnh quét (scanned image) không có text layer.
- Tài liệu nhiều trang đôi (landscape spread) có mật độ thông tin kỹ thuật cao.

## Pipeline Khuyến Nghị
1. **Render ảnh tối ưu:** Dùng `pymupdf` chuyển từng trang PDF sang PNG với DPI phù hợp (150 DPI là điểm cân bằng lý tưởng: chữ Hán nhỏ và số đọc rõ nét, dung lượng base64 ~1.5 - 2.5 MB).
2. **Batching Bounded:** Chia tài liệu thành từng batch nhỏ (3 - 5 trang đôi / batch).
   - Tránh nghẽn HTTP request timeout (>120s).
   - Tránh tràn context window khi LLM sinh bảng Markdown chi tiết.
3. **Lưu trữ độc lập từng phần (`batch_N_pXX_pYY.md`):**
   - Không vội gộp toàn bộ vào một file lớn ngay từ đầu.
   - Giữ nguyên 100% mã hiệu sản phẩm (SKU / Model code) để tiện tra cứu vật tư.
   - Bảng thông số kỹ thuật xuất thành Markdown Table đầy đủ.
4. **Second-Opinion Review Handoff (Claude CLI / External Audit):**
   - Trả từng file batch Markdown hoàn chỉnh cho người dùng.
   - Cho phép người dùng ném trực tiếp từng file vào **Claude CLI** để rà soát đối chiếu chéo (cross-check), kiểm tra tính nhất quán của mã hiệu và thuật ngữ chuyên ngành trước khi thực hiện bước gộp (merge) cuối cùng.
