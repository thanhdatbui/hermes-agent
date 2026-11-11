MobiProxy/R3G/x86 DNAT: Kibe (5101..5138), Admin (5141..5158). x86 Khoa: LAN1 ether3 datlp0, LAN2 ether4 datlp1, LAN3 ether5 datlp2, LAN4 ether6 datlp3 (32 IP, port 5101..5132). Cần rút ether6 khỏi bridge trước khi tạo MACVLAN. 3proxy (172.16.0.2) cần srcnat masquerade 172.16.0.0/24; container 3proxy chỉ sinh cfg lúc tạo nên sửa env không đổi auth (bị 407); Android Wi-Fi proxy không có user/pass nên Kernel DNAT bắt buộc upstream No-Auth + IP Whitelist. DDNS khoa.taadaa.click tự update qua scheduler 1m fetch Cloudflare API. Lệch nick theo sợi quang dính Walled Garden 172.17.x.x (100% loss). R3G: 'default via $peer_ip dev $dev'. Admin PortProxy 192.168.110.119 Tailscale 100.115.94.49. CẤM Direct/xóa proxy GPM/S7. CẤM footer Advisor. Lệnh Done auto-push Git. Chrome CDP: browser_profile port 9222.
§
CẤM tự ý pause/tắt cronjob watchdog khi thấy lỗi (chữa ngọn). Bắt buộc run đọc stderr thật, sửa tận gốc qua unified_patch_pipeline, sync cron_sync_watchdog --force và verify live.
§
tiktok_login_v1.py tự động xử lý tài khoản không mật khẩu bằng luồng OTP; TikTok app Android giới hạn tối đa 8 nick (ẩn nút Thêm tài khoản); 2FA runner tự động kích hoạt trigger_account_reconcile khi gặp ACCOUNT_NOT_IN_SWITCHER hoặc ACCOUNT_MISMATCH_AFTER_SWITCH.
§
GPMLogin: start_profile() tuyệt đối cấm ép ngầm window_pos/win_scale thu nhỏ; luôn mặc định --start-maximized để giữ nguyên scale 100% cho quan sát trực quan.
§
Quy tắc Follow: Dính nhả đuôi (used > 0 rồi mới nhả ở lượt cuối) cấm cộng dồn streak, chỉ tính phạt Streak 1 (nghỉ 24h).
