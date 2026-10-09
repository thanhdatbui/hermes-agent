# Gate 6 — VISUAL EVIDENCE INVARIANT (§VH)
*Được update vào SOUL.md và config.yaml ngày 2026-09-21 sau phiên Codex OAuth*

## Nguyên tắc cốt lõi (Opt-out thay vì Opt-in)
**Mặc định = PHẢI chụp ảnh.** Miễn trừ phải được khai báo tường minh.
Rule cũ Opt-in ("CHỈ chụp khi có hành động thực thi") tạo escape hatch khiến agent tự phán đoán "bước này là trung gian" và chạy loop ngầm không ảnh.

## MAX BLIND STEPS = 1
Tuyệt đối CẤM thực thi quá **1 bước** thao tác UI/Browser/GPM liên tiếp mà không gửi ảnh MEDIA: cho User.

## Các CHỐT CHẶN BẮT BUỘC (MANDATORY CHECKPOINTS)

### CP-1: PRE-ACTION / POST-FILL
*Điền xong form, chọn dropdown xong → BẮT BUỘC chụp ảnh xác nhận dữ liệu đã nằm trên form TRƯỚC khi bấm Submit.*

### CP-2: POST-SUBMIT / RESPONSE
*Bấm nút xong → BẮT BUỘC chụp ảnh NGAY kết quả phản hồi của trang (thành công, lỗi, cảnh báo) trong vòng ≤ 3 giây.*

### CP-3: HEARTBEAT 60s
*Mọi 60 giây nếu tác vụ vẫn đang chạy → chụp trạng thái hiện tại + ghi "HEARTBEAT t+Xs: [trạng thái]".*

### CP-4: ERROR / ANOMALY
*Bất kỳ exception, timeout, redirect lạ → chụp NGAY TRƯỚC khi retry.*

## CẤM FIRE-AND-FORGET
CẤM chạy vòng lặp ngầm (loop) tự thử lại nhiều lần trong bóng tối.
- Thất bại 1 lần → gửi ảnh lỗi ngay.
- Thất bại 3 lần liên tiếp trên 1 tài khoản/thiết bị → **BẮT BUỘC DỪNG NGAY** để báo cáo User.

## ANTI-LOOPHOLE CLAUSES

| Khe hở | Biện pháp chặn |
|:---|:---|
| "Bước này là bước trung gian" | CẤM — không có khái niệm "bước trung gian". Mọi bước = 1 checkpoint. |
| "Gộp nhiều action thành 1 transaction" | CẤM — click → fill → submit phải có ảnh riêng cho mỗi bước. |
| "Anti-spam rule ghi đè Gate 6" | Anti-spam CHỈ áp dụng cho text nhảm. KHÔNG BAO GIỜ áp dụng để né tránh gửi ảnh MEDIA:. |
| "Ảnh này không có giá trị" | Coordinator KHÔNG có quyền phán đoán ảnh nào "không đáng gửi". |

## DANH SÁCH MIỄN TRỪ (EXHAUSTIVE — không mở rộng thêm)
- [EX-1] Bước thuần tính toán nội bộ (không I/O, không UI).
- [EX-2] Sleep/wait ngắn < 5 giây và không thay đổi state.
- [EX-3] Đọc file local không liên quan UI.

## XỬ LÝ KHI VI PHẠM
1. DỪNG NGAY tác vụ hiện tại.
2. Chụp trạng thái hiện tại.
3. Báo cáo: "VI PHẠM §VH: Đã chạy [N] bước mù từ [checkpoint cuối]. Trạng thái: [ảnh]. Yêu cầu xác nhận tiếp tục."
4. KHÔNG tự ý tiếp tục cho đến khi User phản hồi.

## Lý do thay đổi từ Gate 6 cũ
Gate 6 cũ (trước 2026-09-21):
- "CHỈ KÍCH HOẠT khi báo cáo kết quả của một HÀNH ĐỘNG THỰC THI..."
- "CẤM SPAM: Nếu không thực thi hành động can thiệp... CẤM đính kèm MEDIA:"
→ Hai điều này tạo khe hở: agent coi loop thử SIM là "bước trung gian", chạy ngầm 30+ lần, không gửi ảnh nào.
→ User không biết form có điền đúng không, số điện thoại có được nhập chưa, OpenAI phản hồi gì.
→ Dẫn đến tài khoản bị rate-limit, mất thời gian, mất niềm tin vào agent.

Gate 6 mới (§VH, 2026-09-21):
- Đảo ngược: Default = PHẢI chụp. Miễn trừ = khai báo rõ ràng.
- Max Blind Steps = 1 (hard cap).
- Anti-spam chỉ áp dụng cho text chat, KHÔNG được dùng để né ảnh.
