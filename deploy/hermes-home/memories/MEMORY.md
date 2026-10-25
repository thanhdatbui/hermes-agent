Follow TikTok: used >= 1 dính nhả = reset streak 0, phạt 24h, giữ probation/graduated; used == 0 mới tính streak (Streak 1 phạt 24h). Worker 100% dùng Sol (:20129 Free qua dispatch_worker.py), cấm gọi claude_worker trực tiếp từ terminal (exit 126).
§
Worker floor >= 300s, cấm tự bóp timeout. Follow: Streak 1 cd 24h, S2 3d, S3 5d, S4+ 15d; fl >= 1 -> fail_streak=0 ngay; Quota probation độc lập fail_streak.
§
Gate & Hook Invariant: CẤM Veto Gate câm; 100% hook/guard chặn bắt buộc phải trả về Guidance kiến trúc + required_action có lệnh thoát O(1) hoặc instruction. Cấm lách Tier 1 Sol Worker (:20129 100% Free) qua terminal.
§
TikTok follow: Streak 1 cd 24h, Streak 2 cd 3d, Streak 3 cd 5d, Streak 4+ cd 15d. Follow >=1 thành công lập tức reset fail_streak=0; Quota (Hồi phục 1/2/Khỏe) độc lập qua probation_clean_days.