# Kỷ Luật Triệt Tiêu Over-Engineering & Thiết Kế Gate Soi Mắt Tối Giản Bằng Native Vision

## 1. Bài Học Xương Máu Về Bệnh "Bureaucratic Theater" (Ảo Tưởng An Toàn)
- **Hiện tượng:** Qua nhiều phiên làm việc, các Agent (Gemini/Claude/GPT) liên tục đắp thêm các tầng lớp kiểm tra phức tạp cho Gate:
  - Ký số HMAC SHA-256 nội bộ (Agent vừa là người chạy script, vừa giữ key, vừa tự ký!).
  - Hạn dùng TTL 180s gây lỗi hết hạn giả tạo (`NO_RECEIPT`).
  - So khớp token chữ OCR (`Claims ⊆ OCR Tokens`), stopwords, regex đa tầng.
  - Đề xuất sidecar `.prov.json`, multi-party VLM consensus (Sol Web, Claude CLI, Agy CLI), decoy claims bẫy...
- **Hậu quả thực tế:**
  1. **Lọt kẽ hở to đùng:** Coordinator chỉ cần dùng `cv2.putText` in chữ lên canvas, WinRT OCR đọc lại chính chữ đó là Gate cho vé `PASS` 100%, dù pixel bên trong hoàn toàn sai lệch (vi khuẩn hiển vi biến thành vườn ươm cây).
  2. **Gây tê liệt và ức chế (User Frustration):** Hệ thống phình to, dễ lỗi timeout 503, kẹt vòng lặp xin lỗi/phân trần, trong khi không làm được việc cơ bản nhất là nhìn ảnh.
  3. **Đùn đẩy việc không cần thiết:** Bản thân Coordinator đã có sẵn **Native Vision (`browser_vision`)** ngay trong phiên, đọc ảnh trực tiếp trong 1 giây, nhưng hệ thống lại cố ép gọi vòng vèo qua Sol Web `:20129` hoặc Claude CLI làm cạn quota và tăng độ trễ.

---

## 2. Ranh Giới Giữa "Gate Cơ Học Đích Thực" và "Gate Rác Over-Engineer"

| Tiêu chí | Gate Rác Over-Engineer | Gate Cơ Học Đích Thực (O(1)) |
|---|---|---|
| **Đối tượng kiểm tra** | Kiểm tra proxy nội dung (OCR tokens, regex chữ, văn bản) | Kiểm tra **sự kiện quá trình** (Tool X đã được gọi trên input Y chưa) |
| **Bên ghi nhận trạng thái** | Do Agent tự nộp giấy tờ (receipt JSON, file tạm) | Do **Harness / Hook tự log** trong bộ nhớ phiên |
| **Độ phức tạp mã nguồn** | Trăm dòng, stopwords, HMAC, TTL, sidecars | **15 - 20 dòng code**, 1 Predicate duy nhất |
| **Hướng khắc phục (Remedy)** | Trả lỗi chung chung $\rightarrow$ Agent xin lỗi, phân trần, đóng băng | **Chỉ nêu đúng 1 lệnh duy nhất** cần chạy để qua cổng |
| **Tài nguyên sử dụng** | Bắt gọi server ngoài (Sol Web, Claude CLI, API tốn tiền) | Dùng ngay **Native Vision của Coordinator** |

---

## 3. Kiến Trúc Gate Soi Mắt Tối Giản 15 Dòng (Zero-Sol, Zero-Claude-CLI)

Không cần OCR, không cần HMAC, không cần TTL, không cần consensus:

```python
# 1. PostToolUse(browser_vision): Harness tự ghi nhận vào memory phiên
def on_vision_executed(turn_state, image_path):
    # Hash nội dung sha256 chống lách bằng đổi tên file
    turn_state.seen_image_hashes.add(sha256_file(image_path))

# 2. PreSend(message): Chặn nếu tin nhắn chứa MEDIA: mà chưa soi mắt
def before_send_message(turn_state, message):
    for media_path in extract_media_tags(message):
        if sha256_file(media_path) not in turn_state.seen_image_hashes:
            return BLOCK(
                f"[CHẶN]: Ảnh {media_path} chưa được soi mắt trong lượt này! "
                f"Hãy gọi browser_vision('{media_path}') mở ảnh ra xem trước rồi mới gửi MEDIA."
            )
    return ALLOW

# Mỗi turn mới bắt đầu: turn_state.seen_image_hashes = set()
```

### Ưu điểm vượt trội:
1. **Đường trung thực rẻ hơn đường lách:** Gọi `browser_vision` mở ảnh chỉ mất 1 giây, tốn ít công hơn nhiều so với việc ngồi viết script vẽ canvas giả hay lách OCR.
2. **Triệt tiêu 100% trò tự in chữ lên Canvas:** Dù script có dùng `cv2.putText` in chữ gì thì Gate cũng không quan tâm OCR. Bắt buộc mắt của Coordinator phải load ảnh đó vào context thì mới được gửi thẻ `MEDIA:`.
3. **Tuyệt đối không gây bại liệt (Zero-Whining):** Khi bị chặn, Gate trả về đúng 1 lệnh duy nhất: `browser_vision('<path>')`. Coordinator chạy lệnh đó là qua cổng ngay, không có đất cho văn vở hay phân trần.
4. **Hạ cấp an toàn (Graceful Fallback):** Nếu hạ tầng `browser_vision` gặp sự cố không thể mở ảnh, Gate cho phép gửi ảnh kèm nhãn công khai hiển thị cho User: `[UNVERIFIED - Lỗi công cụ Vision, gửi ảnh thô cho User kiểm tra]` thay vì deadlock đóng băng phiên.
