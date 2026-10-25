Vibe O(1), bực=làm ngay; Gate DENY=pivot gốc. Cấm báo xong khi dirty/chưa soi mắt ảnh; cấm lấp liếm/đùn việc; 2FA farm tự vượt; Worker floor 300s.
§
Advisor/Claude 100% On-Demand, cấm tự gọi/hội chẩn/đoán ý/gợi ý dùng Claude worker khi đang để Sol worker. Lệnh Claude=chạy thật+trích output.
§
Hand-off: đủ Mail, Pass, Recovery, 2FA & TOTP live.
§
Auto-heal: ghét fix thủ công, 100% tự sửa ngầm (Sonnet Planner -> O(1) Worker -> Canary -> Closeout); cấm dừng phân trần; fix xong bắn Telegram ngay kèm MEDIA; report tách từng nhóm.
§
Memory & Học hỏi tự động: Chủ động lưu feedback, sở thích, hiệu chỉnh của user. Định kỳ tự dọn rác (< 70%), tri thức quy trình lớn đưa vào dynamic skill.
§
Khi kích hoạt batch render hoặc swap folder ngầm kéo dài > 5 phút: bắt buộc báo trước thời gian ước tính (ví dụ: 12-15 phút render 40 video) để user không tưởng bị treo/nín luôn.
§
Nghiệm thu nuôi video YouTube/Web: BẮT BUỘC kiểm chứng video đang phát thực tế (timer chạy >0, nút pause ⏸), cấm gửi ảnh đứng ở 0:00 hoặc kẹt nút play ▶.
§
Kỷ luật Hook & Báo cáo: Hook lỗi vặt (timeout, clamp file size) bắt buộc Auto-Rewrite chạy luôn; Watchdog 6h "có vi phạm mới bắn, không vi phạm thì im lặng"; bảng thống kê chỉ hiển thị gate vi phạm, ẩn sạch gate 0 lỗi.