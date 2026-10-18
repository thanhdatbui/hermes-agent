# RCA & Khắc Phục: Vi Phạm Gate 6 Khi Báo Cáo Tiến Độ (The Narrative Bypass Trap)

*Thời điểm ghi nhận:* 18/10/2026
*Thẩm định độc lập:* Claude Sonnet 5.5 CLI (`--role planner`)

## 1. Sự Cố Thực Tế
Trong phiên điều phối ghim video và cập nhật bio trên Máy 23 (`@huynhdiem0806`), sau khi các subagent hoàn thành chuỗi thao tác, Coordinator đã gửi một tin nhắn thuần văn bản giải thích tiến độ / trần thuật hiện tượng:
> *"Báo cáo tổng kết hiện trường sau khi toàn bộ chuỗi subagent hoàn tất... Video top view đã được ghim thành công... Kịch bản cập nhật chuỗi bio mới đã được subagent thực thi... Subagent cuối đã tắt hoàn toàn popup trả về profile sạch..."*

Tin nhắn này hoàn toàn không có thẻ `MEDIA:<path>`, vi phạm trực tiếp Invariant Gate 6. Operator lập tức cảnh báo gắt gao: *"Hình ảnh đâu. Xây dựng gate phải gửi hình sau khi xong rồi mà, lại vi phạm tiếp?"*.

## 2. Vì Sao Hook Regex Bị Lọt? (RCA Từ Claude Sonnet 5.5)
1. **Lỗ hổng Denylist theo từ khóa:** Regex cũ chỉ chặn các câu khẳng định thành công trực diện (`đã hoàn tất`, `đã đổi`, `đã xong`). Khi Coordinator dùng lối hành văn trần thuật hiện trường (`Báo cáo hiện trường...`, `kịch bản đã được thực thi...`), regex không kích hoạt chặn -> Fail-Open.
2. **Sai tầng kiểm soát:** Bộ kiểm tra chưa được đưa vào tầng Egress / Stop Hook của Agent để chặn đứng tin nhắn trước khi bắn ra Telegram.
3. **Mù ngữ cảnh thiết bị (Context-Blindness):** Không có cơ chế tự động nhận diện: Khi trong phiên có lời gọi ADB/thiết bị thì tin nhắn trả lời bắt buộc phải có thẻ MEDIA.

## 3. Kiến Trúc Khắc Phục Cơ Học Fail-Closed
- **Context Trigger:** Bất kỳ lượt hội thoại nào có tương tác với thiết bị Android thật (ADB, touch, runner, lock).
- **Contextual Allowlist:** Tin nhắn cuối cùng chỉ được phép xuất ra nếu có thẻ `MEDIA:<path>` kèm receipt fresh, hoặc mở đầu bằng `STATE: UNVERIFIED` nếu xảy ra sự cố vật lý.
- Mọi trường hợp trần thuật bằng văn bản suông đều bị chặn đứng ở tầng Egress với mã `BLOCKED_NO_EVIDENCE`.
