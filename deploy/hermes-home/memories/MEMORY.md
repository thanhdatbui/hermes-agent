MikroTik Web (:2310) quản lý PPPoE Đà Nẵng; R3G Thái Bình (16 port 5141-5158) quản lý tại Dashboard :1905, status/uptime/IP lấy trực tiếp qua OpenWrt ubus dump (uptime tiếng Việt, IP WAN); proxy nuôi farm mặc định đứng im, cấm cron spam generate_all_proxies.sh làm reboot router. Gate 6 cấm bốc nhầm ảnh từ image_cache.
§
Niche: Video là Ground Truth. CẤM cào tin tức/VTV/phóng sự (dính bóp reach); đổi nguồn dọn sạch render+gốc -> cào/render mới. Niche đề xuất cao: Câu chuyện (Top 1, 31k tim), Giao thông, Gym; Ẩm thực là bẫy flop (4.1 tim/clip, 20% flop, cấm đề xuất bừa). Chuẩn hoá: lookup_channel.py; ghim: pin_top_videos.py. Uncalled Action Mandate (conversation_loop: 3 lần ép tool, cấm buông xuôi/hứa suông). Hermes SSOT: D:\Taadaa\Hermes\.venv.
§
Gate 6: watchdog retry, evidence tự tính. S4 canary_plan.py --plan. S7 toàn farm (Kibe+Admin) bắt buộc volume=0 ban đêm chống ồn; TikTok ko phạt mute.
§
Canary: phân tầng UI vs Backend (backend ko screencap). Lock repo: single-writer. SQLite SSOT: `tiktok_workflow_state` & `tiktok_accounts` trong `farm_master.db` (DAL `farm_sqlite_dal.py`, WAL). 2FA SSOT: Đã khử 100% Excel trong `tiktok-add-bao-mat-f2a` (commit e6acad5). S7 kẹt kick 'adb reconnect offline'. M10/30/35/41 Kibe & M255 rớt USB. Runner & watchdog cấm phụ thuộc Excel runtime.
§
Telegram Proxy: Viettel LAN :10001 primary, WARP :40000 fallback, Heartbeat 30s; httpx.ReadTimeout bắt buộc nằm trong retryable error của MultiISPTransport tránh bẫy wedged getUpdates queue ngâm 3-5m.
§
Nén: threshold 0.6, protect 50, aux=gemini-web, timeout 300s. Tỉa thô <600k dừng ngay, cấm LLM nén giữ cache. Cấm nén backend OmniRoute. Pool gemini-web 20 acc Pro MobiProxy; cấm IP Direct. Worker: Tier 1 Gemini Web (timeout 300s/turn, floor 480s, 12 turns) -> Tier 2 Sol -> Tier 3 Agy -> Tier 4 Haiku. Qoder hết hạn 31/10.
§
R3G Thái Bình (16 port 5141-5158): Uptime & IP lấy native từ `ubus call network.interface dump`; cấm cron killall tinyproxy; tắt watchcat ping_reboot; giữ overlay <75%. MikroTik watchdog-pppoe chỉ reset private IP 172.16..31, cấm đụng 172.x public và pppoe-out1 (Whitelist MobiProxy). Container logging tắt chống nghẽn CPU. Proxy đứng im 24/7.