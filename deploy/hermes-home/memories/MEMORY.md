Guard_media_vision_gate chặn DIRTY_AVATAR_EVIDENCE, cấm leak DEGRADED ra chat; kiểm tra contradiction phổ quát cho mọi loại ảnh để chống AI bịa đặt thành công khi ảnh hiển thị lỗi.
§
Nạp ChatGPT-Web: trần 2 acc/IP + proxy_assignments; worker <= 5; Hotmail là mail mua sẵn (mail kp smvmail.com/fviainboxes có public API đọc OTP, cấm than thở thiếu mail kp); pass ChatGPT random độc nhất lưu Excel; script reg cấm exit 0 khi fail; lọc GPM GroupId!=0; pre-validate Graph token; cấm base64.
§
Watchdog đối soát TikTok Web: đối chiếu Username; runner timeout salvage từ state; 3 quy trình Feed-Follow-Upload độc lập hoàn toàn (cái nào fail thì cái khác vẫn chạy); cấm phạt cooldown 24h chỉ sau 1 lần nhả follow (streak >= 2); Quota Khỏe [cap-2, cap], tái tốt nghiệp bóp trần = last_failed_ceiling - 2; Path B verify profile BẮT BUỘC giữ pull-to-refresh để bắt nhả thật (cấm gỡ), chống lag bằng sleep_after 3.5s + polling 2 nhịp.
§
Tool 2FA và cron xen ca: JIT lock từng máy (cấm bulk pre-reserve); freeze_targets bọc retry 5 nhịp backoff + dọn lock mồ côi ~$*.xlsx né xung đột cron sync 5m; Batch 2FA Admin qua SSH bắt buộc --adb-path r"C:\Program Files (x86)\xiaowei\tools\adb.exe"; sau sửa 2FA bắt buộc chạy sync_2fa_to_admin.py.
§
GuardGate (D:/Taadaa/tools/guardgate) là Protection Regression Gate cơ giới hóa cho code diff repo (Closeout Step 2.5); infra_regression_gate.py chỉ kiểm tra riêng 4 file config hạ tầng Hermes/OmniRoute.
§
Code sửa mới >= 15 dòng bắt buộc phân bước rõ ràng (# Bước X / # Step X); cấm cam kết miệng mà bắt buộc cơ giới hóa qua GuardGate rules.json từng repo.
§
Lệnh dispatch_worker qua terminal bắt buộc timeout >= 480s khớp sàn sol_worker, cấm set 180s làm rớt session.
§
Khi deploy router OpenWrt headless (Xiaomi R3G): Nếu WAN mất internet/Walled Garden (!C), 'tailscale up' sẽ treo TLS timeout. Kiểm tra ISP device (H196A) có tự quay chiếm PPPoE (Type: Routing) hay OLT khóa MAC; clone MAC qua Override MAC address trong LuCI nếu cần. Nhắn tin kỹ thuật ISP luôn lịch sự, chuyên môn, dẫn chứng ICMP !C và account ID.