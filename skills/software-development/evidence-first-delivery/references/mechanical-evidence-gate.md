# Mechanical Evidence Gate & Anti-Replay Protocol

Tài liệu kỹ thuật chuẩn hóa cho cơ chế kiểm chứng bằng chứng thị giác cơ học độc lập (Mechanical Evidence Gate Engine) được phát triển và thẩm định qua nhiều vòng audit bởi Claude Code CLI.

---

## 1. Các Bẫy & Lỗ Hổng Trọng Yếu Khi Báo Cáo Bằng Chứng (Audit Findings)

Trong quá trình tự động hóa tác vụ UI (Browser, Farm, App, GPM), các agent dễ mắc phải các điểm mù nhận thức (Confirmation Bias) hoặc tạo ra các kẽ hở kiểm chứng:

1. **Bẫy Stale Error Banner (Vết Lỗi Cũ Khi Retry):**
   - Khi thực hiện retry sau một lần nhập sai (ví dụ: OTP sai -> hệ thống báo lỗi đỏ -> bốc lại mã đúng và điền lại), trên màn hình thường vẫn lưu lại vệt chữ báo lỗi của lần thử trước đó cho đến khi bấm nút Submit mới.
   - Nếu chụp ảnh Pre-submit lúc này, OCR sẽ đọc được chữ báo lỗi đỏ và có thể bị nhầm lẫn là lần thử mới đã thất bại, hoặc tệ hơn là agent tự hợp thức hóa bằng cách khai báo "đây là lỗi cũ".

2. **Lỗ Hổng Replay Ảnh Cũ (Stale Artifact Replay Attack):**
   - Agent hoặc quy trình tự động có thể tái sử dụng một ảnh chụp màn hình sạch từ một phiên làm việc trước đó hoặc từ tác vụ khác làm ảnh `post_image` để lừa gate bỏ qua lỗi thực tế.
   - **Khắc phục:** Bắt buộc kiểm tra dấu vết thời gian vật lý (Temporal Ordering):
     * `post_image.mtime >= pre_image.mtime`
     * Thời gian cách biệt giữa hai ảnh không vượt quá cửa sổ thao tác: `post_mtime - pre_mtime <= 120s`.
     * Tuổi thọ của artifact không vượt quá ngưỡng phiên: `now - mtime <= 600s`.

3. **Lỗ Hổng Fake Pairing (Cùng 1 File Ảnh):**
   - Agent chỉ truyền 1 ảnh duy nhất cho cả `pre_image` và `post_image` hoặc copy clone file.
   - **Khắc phục:** Bắt buộc tính mã băm SHA-256 và so sánh `pre_hash != post_hash`, chứng minh có sự chuyển đổi trạng thái giao diện UI thực sự.

4. **Lỗ Hổng Self-Attestation (Tự Khai Báo Lỗi Để Lách Luật):**
   - Cho phép caller/agent truyền chuỗi lỗi tùy ý (`--prev-error`) để tự nhận diện lỗi cũ -> Agent có thể tự khai báo bất kỳ lỗi nào đang hiển thị là "lỗi cũ" để lách qua VETO.
   - **Khắc phục:** Zero Self-Attestation. Trạng thái lỗi cũ chỉ được công nhận cơ học khi: `pre_image` có vệt lỗi nhưng `post_image` hợp lệ, sạch lỗi 100%, có SHA-256 khác biệt và thỏa mãn ràng buộc thời gian.

5. **Lỗ Hổng Substring False-Positive & Unicode Normalization:**
   - So khớp chuỗi dạng substring (`kw in text`) dẫn đến các lỗi match nhầm nghiêm trọng (ví dụ: keyword `"error"` khớp nhầm trong từ `"terror"` hoặc `"crash"` trong `"crashlytics"`).
   - Sự khác biệt bảng mã Unicode (NFC vs NFD) giữa OCR engine và keyword list dẫn đến miss-detect lỗi tiếng Việt.
   - **Khắc phục:** Bắt buộc chuẩn hóa Unicode NFC và sử dụng Regex Word Boundaries: `(?:\b|^)kw(?:\b|$)`.

6. **Thiếu Bằng Chứng Dương Tính (Affirmative Success Evidence):**
   - Màn hình sạch chữ hoặc ảnh trắng không đồng nghĩa với tác vụ đã thành công.
   - **Khắc phục:** Ngoài việc quét vắng mặt tín hiệu lỗi, kiểm tra sự xuất hiện của các từ khóa thành công thực sự (`removed`, `added`, `updated`, `success`, `đã xóa`, `đã thêm`, `hoàn tất`...).

---

## 2. Đặc Tả Công Cụ `evidence_gate_verifier.py`

Công cụ chuẩn hóa đặt tại: `D:/Taadaa/tools/evidence_gate_verifier.py`

### CLI Interface:
```bash
python D:/Taadaa/tools/evidence_gate_verifier.py \
  --pre-image "D:/path/to/pre.png" \
  --post-image "D:/path/to/post.png" \
  --claim "Đã đổi mail khôi phục thành công" \
  --expected-post-keywords "removed" "added" \
  --elapsed-seconds 12.5
```

### Các Giá Trị Verdict Chuẩn:
- `PASS`: Cả 2 ảnh đều sạch lỗi, khác biệt SHA-256, thỏa mãn mtime sequence.
- `FLAGGED_STALE_RESOLVED`: `pre_image` có vệt lỗi cũ từ lần thử trước, nhưng `post_image` mới hơn, sạch 100% lỗi và có SHA-256 khác biệt -> Chuyển đổi trạng thái thành công được chứng minh cơ học.
- `VETO_REJECT`: `post_image` chứa tín hiệu lỗi, hoặc `pre_image` chứa lỗi nhưng thiếu `post_image` sạch để giải tỏa. Tuyệt đối cấm phát ngôn thành công!
- `ESCALATE_L3_BLOCKED`: Quá ngưỡng an toàn (`elapsed > 30s` HOẶC `attempts >= 3`).
- `FAIL`: Thiếu file ảnh, file ảnh hỏng/rỗng (<1KB, sai header PNG/JPEG/WEBP), vi phạm mandatory pairing hoặc phát hiện replay ảnh cũ.

---

## 3. Cryptographic Hash-Chained Audit Ledger

Mọi kết quả kiểm chứng đều được ghi đồng thời vào 2 nơi:
1. File JSON chi tiết: `D:/Taadaa/runtime/audit/evidence_gate_<timestamp>_<uuid>_<verdict>.json`.
2. Sổ cái nối chuỗi bất biến (Append-only Ledger): `D:/Taadaa/runtime/audit/audit_chain.jsonl`.
   Mỗi bản ghi chứa:
   - `run_id`, `timestamp`, `verdict`
   - `pre_image_sha256`, `post_image_sha256`
   - `prev_hash`: SHA-256 của khối trước đó
   - `block_hash`: SHA-256 của toàn bộ khối hiện tại (bao gồm `prev_hash`).

Cơ chế này ngăn chặn tuyệt đối việc xóa, sửa hoặc chèn lậu các bản ghi audit trail trong quá trình vận hành farm.
