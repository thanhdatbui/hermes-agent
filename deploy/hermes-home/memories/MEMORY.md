Guard_media_vision_gate chặn DIRTY_AVATAR_EVIDENCE, cấm leak DEGRADED ra chat; kiểm tra contradiction phổ quát cho mọi loại ảnh để chống AI bịa đặt thành công khi ảnh hiển thị lỗi.
§
Nạp ChatGPT-Web: trần 2 acc/IP + proxy_assignments; worker <= 5; Hotmail là mail mua sẵn (mail kp smvmail.com/fviainboxes có public API đọc OTP, cấm than thở thiếu mail kp); pass ChatGPT random độc nhất lưu Excel; script reg cấm exit 0 khi fail; lọc GPM GroupId!=0; pre-validate Graph token; cấm base64.
§
Watchdog đối soát TikTok Web: Chu kỳ farm 3-4 ngày/acc (1 ca/buổi gồm 2 phiên cách nhau >= 120m); Quota max cap 40 fl/ngày (cấm bịa vạch đỏ 30); used>0 streak luôn=1 (cooldown 24h xả sạch trước vòng sau), chỉ used=0 mới tăng streak; cấm bịa nhả ngược; 3 quy trình Feed-Follow-Upload độc lập; Quota [cap-2, cap], bóp trần = last_failed - 2; A/B test Max Volume: Máy Lẻ (Nhóm A bám trần + hồi phục 1,2), Máy Chẵn (Nhóm B max 20 fl/phiên x 2=40, used>0 chạm trần dừng nhận số fl đã ăn và BỎ HỒI PHỤC 1,2; used=0 mới cooldown).
§
Tool 2FA và cron xen ca: JIT lock từng máy (cấm bulk pre-reserve); freeze_targets bọc retry 5 nhịp backoff + dọn lock mồ côi ~$*.xlsx né xung đột cron sync 5m; Batch 2FA Admin qua SSH bắt buộc --adb-path r"C:\Program Files (x86)\xiaowei\tools\adb.exe"; sau sửa 2FA bắt buộc chạy sync_2fa_to_admin.py.
§
GuardGate (D:/Taadaa/tools/guardgate) là Protection Regression Gate cơ giới hóa cho code diff repo (Closeout Step 2.5); infra_regression_gate.py chỉ kiểm tra riêng 4 file config hạ tầng Hermes/OmniRoute.
§
Dashboard TikTok (1905, tiktok_dashboard.py) độc lập 100% với Farm runner (tiktok_runner.py); cấm suy diễn lỗi Dashboard sang Farm. Watchdog restart service Windows phải kill cả cây pythonw.exe + python.exe để tránh đụng socket SO_REUSEADDR gây treo/sập.
§
Canary visual: cấm dùng ảnh transition spinner ('Quá trình này có thể mất...', loading); bắt buộc mtime ảnh >= mtime UI dump và soi mắt settled state.