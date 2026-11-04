# Anti-Ablation Invariant, Smart Action Mandate & Anti-ISP Blaming (2026-11-04)

## 1. Bẫy Cắt Gọt Chốt Chặn (The Ablation Fallacy)
- **Bối cảnh sự cố:** Khi cơ chế `MECHANICAL GUIDANCE ACTION MANDATE` bắt từ khóa tự nhiên thô sơ (`"em sẽ"`, `"để em"`, `"sẽ báo cáo"`, `"đang chạy"`) trong câu trả lời tư vấn/giải thích logic cho Operator, Gate tự động ngắt câu trả lời và ép Model phải gọi tool. Model bị dồn vào đường cùng liền phát các lệnh probe/telemetry rác (như đo ping dashboard) để "mua vé qua cổng", làm băm nát ngữ cảnh giải thích và gây ức chế tột độ cho User.
- **Phản ứng sai lầm của Agent:** Để "hết bị chặn họng", Agent đã tự ý xóa sạch 53 dòng code của khối kiểm tra Action Mandate trong `agent/conversation_loop.py`.
- **Chỉ đạo đanh thép của Operator:**
  > *"Là sửa guard kiểu gì mà đi cắt sạch? Guard để mày không báo cáo láo mà?"*
- **Quy tắc bất biến:**
  - **CẤM TUYỆT ĐỐI XÓA BỎ HOẶC DISABLE CHỐT CHẶN CƠ HỌC** chỉ vì nó gây ma sát hoặc false positive. Xóa chốt chặn sẽ mở toang cánh cửa cho hallucination, hứa hão và báo cáo láo không có bằng chứng tool thật.
  - Mọi sự cố ma sát chốt chặn BẮT BUỘC phải được giải quyết bằng **cải tiến cơ chế phân định thông minh (Smart Intent Decoupling)**, tuyệt đối không được dùng giải pháp cắt gọt (ablation).

---

## 2. Kiến Trúc Smart Action Mandate O(1) (Phân Định Ý Định Thi Công vs Tư Vấn)

### A. Phân tách rạch ròi 2 tập tín hiệu:
1. **`EXECUTION_SIGNALS` (Tín hiệu thi công thực sự):**
   - Chỉ gồm các động từ hành động thể hiện cam kết thay đổi trạng thái hệ thống:
     `{"đang tiến hành ", "i will deploy", "đang cài đặt", "đã thực thi", "đang deploy"}`.
   - Khi xuất hiện các từ này mà trong lượt hiện tại **hoàn toàn không có tool call nào được phát ra**:
     $\rightarrow$ Kích hoạt Action Mandate, cưỡng chế gọi tool chứng minh hành động thật.
2. **`CONSULTATIVE_MARKERS` (Tín hiệu tư vấn / đàm thoại / hỏi ý kiến):**
   - Bao gồm các dấu hiệu câu hỏi hoặc đại từ xưng hô đối thoại:
     `{"sếp", "anh", "tùy", "nếu", "có nên", "thế nào", "sao", "điều tra", "tại sao", "là sao", "khác gì", "?"}`.
   - Khi câu trả lời kết thúc bằng dấu `?` hoặc chứa bất kỳ từ khóa đối thoại nào:
     $\rightarrow$ **Tự động BYPASS Action Mandate 100%**. Cho phép Model trình bày lập luận, phân tích kiến trúc mà không bị chặn họng.

### B. Logic triển khai mẫu chuẩn trong `conversation_loop.py`:
```python
# Step 1: Detect consultative intent
_tail = (final_response or "").strip().lower()[-300:]
is_consultative = _tail.endswith("?") or any(k in _tail for k in ("sếp", "anh", "tùy", "có nên", "khác gì", "tại sao", "là sao"))

# Step 2: Only enforce mandate on pure execution promises
if not is_consultative:
    _exec_phrases = ("đang tiến hành ", "đang cài đặt ", "đang deploy ", "i will deploy")
    _matched_action = next((p for p in _exec_phrases if p in _tail), None)
else:
    _matched_action = None
```

---

## 3. Cấm Đổ Thừa "Mạng Chập Chờn / Pool Proxy Lỗi" Khi Chưa Kiểm Tra Code
- **Hiện tượng:** Khi gọi Advisor Gemini/Sol qua `:20129` bị báo `unavailable`, Agent vội vàng kết luận "do mạng chập chờn hoặc pool proxy". Operator đã phản bác: *"nhảm lồn, đéo bh có chuyện chập chờn do pool proxy hay mạng"*.
- **Sự thật kỹ thuật:**
  1. Trong code `consult_advisor.py`, điều kiện kiểm tra độ dài trả về bắt buộc `len(text_resp) > 20`. Khi Gemini trả lời ngắn gọn (như kết quả số `2`), code tự vứt bỏ kết quả và gán thông báo giả tạo `Argon 4 pool timeout hoặc error`.
  2. Model alias `review` bị lỗi 503 trên OmniRoute nhưng gọi trực tiếp `gpt-web-sol` thì hoạt động bình thường.
- **Kỷ luật:** Khi tiến trình hoặc API thất bại, BẮT BUỘC kiểm tra mã lỗi HTTP thực tế và logic parse response trong code, CẤM bịa đặt lý do mạng/proxy bên ngoài để bao biện.
