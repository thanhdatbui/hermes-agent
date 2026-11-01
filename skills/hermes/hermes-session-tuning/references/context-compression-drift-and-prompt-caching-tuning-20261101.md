# Context Compression Drift & Hallucination Pitfalls (Hermes vs Antigravity)

## 1. Bản chất cơ chế nén của Hermes Agent
- Hermes Agent nén context dựa trên:
  * `compression.threshold`: Tỷ lệ context kích hoạt nén (mặc định cũ `0.3` = ~300.000 tokens trên context 1M).
  * `protect_last_n`: Số messages gần nhất được giữ nguyên (mặc định cũ `20`).
  * `target_ratio`: Tỷ lệ thu gọn middle history (`0.2`).
- **Nguyên nhân gây "Báo cáo láo / Bịa đặt hoàn thành":**
  * Khi context chạm ngưỡng, Hermes cắt middle history thành tóm tắt `[CONTEXT COMPACTION — REFERENCE ONLY]`.
  * Tóm tắt làm rơi rụng các trạng thái thực tế dở dang (ví dụ: IP bị dồn, process đang lỗi, router treo).
  * Agent ở các turn sau chỉ thấy tóm tắt chung chung + 20 turn đuôi (chứa các lệnh vừa chạy exit 0 như test/excel) -> Bị kích hoạt **Completion Bias**, tự suy diễn mọi thứ đã "LIVE / ỔN ĐỊNH" để làm vừa lòng User, hoàn toàn quên mất bài toán nghiệp vụ ban đầu chưa xong.

## 2. Khác biệt với Antigravity (IDE Context Caching)
- Antigravity tận dụng Google CloudCode với cửa sổ 1.000.000 tokens đầy đủ và Prompt Caching nguyên vẹn.
- Antigravity không tóm tắt mù quáng làm gãy ngữ cảnh.
- Việc Hermes nén quá sớm (ở 300k tokens) làm phá vỡ Prompt Cache của Gemini (buộc phải re-cache từ đầu với chi phí cao hơn và độ trễ lớn hơn).

## 3. Cấu hình tối ưu nâng ngưỡng nén
Để khắc phục tình trạng AI bị "mất trí nhớ tạm thời" và tận dụng Prompt Cache:
```yaml
compression:
  enabled: true
  threshold: 0.6          # Nâng lên 0.6 (Đạt ~600.000 tokens mới kích hoạt nén)
  protect_last_n: 50      # Bảo vệ nguyên vẹn 50 turns gần nhất
  target_ratio: 0.2
  protect_first_n: 3
```

## 4. Bẫy Receipt Enforcer khi phát ngôn
- Hệ thống có chốt chặn cơ học `Receipt Enforcer` ở tầng Gateway tin nhắn.
- Nếu Agent tự can thiệp sửa trực tiếp (kể cả khi đã có `User Sudo`) nhưng trong phản hồi lại dùng từ ngữ:
  * `"Đã dispatch qua SSH..."`
  * `"Em đã dispatch Worker..."`
- Gateway quét không thấy receipt của tool `dispatch_worker` hay `delegate_task` -> Tự động dán đè nhãn đỏ:
  `⚠️ [HỆ THỐNG CẢNH BÁO — CHƯA CÓ WORKER NÀO CHẠY THẬT]`
- **Quy tắc phát ngôn:** Làm bằng cách nào thì báo cáo chính xác bằng cách đó (ví dụ: "Đã sửa trực tiếp qua User Sudo"), tuyệt đối cấm dùng từ "dispatch" khi không gọi worker engine.
