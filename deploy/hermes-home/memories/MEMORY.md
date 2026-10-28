Guard_media_vision_gate chặn DIRTY_AVATAR_EVIDENCE, cấm leak DEGRADED ra chat; kiểm tra contradiction phổ quát cho mọi loại ảnh để chống AI bịa đặt thành công khi ảnh hiển thị lỗi.
§
Nạp ChatGPT-Web: trần 2 acc/IP + proxy_assignments; worker <= 5; Hotmail là mail mua sẵn (mail kp smvmail.com/fviainboxes có public API đọc OTP, cấm than thở thiếu mail kp); pass ChatGPT random độc nhất lưu Excel; script reg cấm exit 0 khi fail; lọc GPM GroupId!=0; pre-validate Graph token; cấm base64.
§
Watchdog đối soát TikTok Web: đối chiếu Username; runner timeout salvage từ state; 3 quy trình Feed-Follow-Upload độc lập hoàn toàn (cái nào fail thì cái khác vẫn chạy); cấm phạt cooldown 24h chỉ sau 1 lần nhả follow (streak >= 2); 1 ca gồm 2 phiên cách nhau >= 120m; Trần phiên [cap-2, cap] 10-15 fl né burst limit; Trần ngày chuẩn config 40 fl (max 50), cấm bịa vạch đỏ 30; Nick khỏe tự leo tháp min(40, proven+2); Tái tốt nghiệp bóp trần = last_failed_ceiling - 2; Path B verify profile BẮT BUỘC giữ pull-to-refresh để bắt nhả thật (cấm gỡ), chống lag bằng sleep_after 3.5s + polling 2 nhịp.
§
Tool 2FA và cron xen ca: JIT lock từng máy (cấm bulk pre-reserve); freeze_targets bọc retry 5 nhịp backoff + dọn lock mồ côi ~$*.xlsx né xung đột cron sync 5m; Batch 2FA Admin qua SSH bắt buộc --adb-path r"C:\Program Files (x86)\xiaowei\tools\adb.exe"; sau sửa 2FA bắt buộc chạy sync_2fa_to_admin.py.
§
GuardGate (D:/Taadaa/tools/guardgate) là Protection Regression Gate cơ giới hóa cho code diff repo (Closeout Step 2.5); infra_regression_gate.py chỉ kiểm tra riêng 4 file config hạ tầng Hermes/OmniRoute.
§
Khi chẩn đoán mạng OpenWrt/PPPoE: Tuyệt đối không suy diễn lan man các giả thuyết vô lý (như thợ ISP rảnh đi bind MAC cục test H196A); phải soi kỹ cấu hình thực tế trên thiết bị (firewall zone conflict, bridge br-lan, mwan3 blackhole, package rác, Service Name bị điền 'auto'). Lời nói nhắn tin cho thợ/người khác phải nhẹ nhàng, chuẩn mực kỹ thuật, ngắn gọn 1 chạm copy.