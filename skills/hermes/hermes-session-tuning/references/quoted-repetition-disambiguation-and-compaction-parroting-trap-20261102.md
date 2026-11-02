# Quoted Repetition Disambiguation & Session Compaction Parroting Trap

## 1. Bản chất sự cố (Symptom & Root Cause)
- **Hiện tượng**: User gửi phản hồi `?` hoặc `Ủa?` trích dẫn (reply quote) lại một đoạn văn dài trước đó mà AI vừa phát ngôn (ví dụ: đoạn báo cáo hiện trường Máy 223 và môi trường OpenCV). AI hiểu lầm đó là câu hỏi yêu cầu giải thích tiếp về nội dung trong quote hoặc bị kẹt trong bẫy parroting lặp lại nguyên văn báo cáo cũ.
- **Nguyên nhân gốc rễ**: 
  1. **Hiểu sai ngữ cảnh trích dẫn của User**: Dấu `?` kèm trích dẫn đoạn text của bot là **tín hiệu chất vấn/bắt lỗi (Contradiction / Hallucination Alert)**: *"Tại sao mày lại nói đoạn này ở đây?"* hoặc *"Đoạn này liên quan gì đến việc đang làm mà mày lải nhải?"*, hoàn toàn KHÔNG PHẢI là câu hỏi nhờ giải thích chi tiết nội dung trong quote.
  2. **Bẫy Context Compaction Parroting**: Khi session trải qua nén ngữ cảnh (Context Compaction), thông tin về các task phụ hoặc trạng thái vừa giải trình được gom lại trong `Historical Task Snapshot`. Khi gặp tin nhắn ngắn hoặc quote, mô hình có xu hướng bốc lại các thực thể nổi bật trong bản tóm tắt (như Máy 223, OpenCV) để "báo cáo hiện trường" đối phó thay vì đối chiếu xem lệnh hiện tại thực sự là gì.

---

## 2. Quy tắc phản xạ và xử lý chuẩn (Standard Operating Procedure)

Khi User gửi `?` hoặc một tin nhắn cực ngắn trích dẫn lại đoạn chat của Agent:

1. **Nhận diện ngay tín hiệu chất vấn (Challenge Signal)**:
   - Coi ngay đó là cảnh báo Agent đang nói lạc đề, nhầm session, hoặc vừa phát ngôn một đoạn thừa thãi/mâu thuẫn.
   - **CẤM TUYỆT ĐỐI**: Không lặp lại nội dung đã trích dẫn; không tiếp tục phân tích, bổ sung số liệu hay "báo cáo hiện trường" cho thực thể nằm trong trích dẫn đó.

2. **Dừng ngay vòng lặp lặp lại (Break Parroting Loop)**:
   - Thẳng thắn chỉ rõ sự cố: Nhận biết ngay việc trích dẫn là do đoạn chat vừa rồi bị lệch bối cảnh hoặc dư thừa sau compaction / gateway retry.
   - Tóm tắt đúng **1 câu** về việc đoạn text đó xuất phát từ đâu (ví dụ: tồn đọng từ phiên cũ về avatar/máy 223).

3. **Truy vấn hiện trường thực tế & Hướng việc về luồng chính**:
   - Kiểm tra nhanh trạng thái thực tế của các tác vụ đang chạy dở (như git status, các run pipeline đang pending hoặc task user giao trước đó).
   - Đưa ra 2 lựa chọn dứt khoát về task nghiệp vụ kế tiếp để user điều phối, cắt đứt hoàn toàn việc lải nhải phân bua.

---

## 3. Bài học khắc cốt ghi tâm
- Không bao giờ coi một câu trích dẫn ngắn (`?`, `.`, `sao thế`) là yêu cầu mở rộng nội dung trích dẫn. Luôn kiểm tra tính tương thích ngữ cảnh (Context Relevance) giữa đoạn trích dẫn và mục tiêu thực sự của session hiện hành trước khi trả lời.
