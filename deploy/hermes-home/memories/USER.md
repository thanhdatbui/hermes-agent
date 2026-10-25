Vibe O(1), bực=làm ngay; Gate DENY=pivot gốc. Cấm báo xong khi dirty/chưa soi mắt ảnh; cấm lấp liếm/đùn việc; 2FA farm tự vượt; Worker floor 300s.
§
Advisor/Claude 100% On-Demand, cấm tự gọi/hội chẩn/đoán ý/gợi ý dùng Claude worker khi đang để Sol worker. Lệnh Claude=chạy thật+trích output.
§
Hand-off: đủ Mail, Pass, Recovery, 2FA & TOTP live.
§
Auto-heal: ghét fix thủ công, 100% tự sửa ngầm (Sonnet Planner -> O(1) Worker -> Canary -> Closeout); cấm dừng phân trần; fix xong bắn Telegram ngay kèm MEDIA; report tách từng nhóm.
§
Memory & Học hỏi tự động: Cho phép AI chủ động lưu (proactive save) feedback, sở thích, hiệu chỉnh của user và các quirk/kinh nghiệm thực tế. Cơ chế dọn rác định kỳ (Garbage Collection): Định kỳ tự đối soát và gọt bỏ các entry cũ đã được code hóa vào script/hook, duy trì Memory gọn gàng < 70%. Tri thức quy trình đồ sộ thì đưa vào dynamic skill.
§
Khi tạo cronjob chạy ngầm/bảo trì batch, BẮT BUỘC đặt deliver='local'; cấm để deliver='origin' làm tràn stdout/telemetry vào chat Telegram.