MobiProxy/R3G DNAT: Kibe (5101..5138) & Admin (5141..5158). Mangle bypass *174,*175. Killswitch: drop WAN direct, QUIC 443, DNS 53. Skeleton xám = Fail-Closed. Sync DDNS tb.taadaa.click vào NAT. MobiProxy Box v3.0.67 LAN 1. Cron farm_idle_screen_and_app_healer.py.
§
Pipeline & Dual-Node SSOT: unified_patch_pipeline sửa code. Hermes Cron cấm workdir (parallel_pool). Kibe SSH điều khiển Admin (192.168.110.119) tự chạy script ghi SQLite riêng (D:\Taadaa\data\farm_master.db); Kibe Reconcile Pull O(1). OpenSSH Admin cần StrictModes no và quyền ACL Administrators/SYSTEM trên ProgramData\ssh. RepoLock tự dọn dead-owner PID.
§
GPM & Cron: Cron batch lưu fail state (12-24h). GPM login né ca feed. CẤM cấp mail farm gắn TikTok. SQLite farm_master.db (SSOT). Remote PS bắt buộc LastWriteTime. OmniRoute :20129: POST /api/restart để reload. CẤM tự ý xóa acc khỏi combos OmniRoute. CẤM 'npm run build:backend' trên OmniRoute kẻo trắng trang Dashboard. Coordinator cấm chạy qua gemini-web.
§
Kỷ Luật Ground Truth & GPM Session: CSDL/Excel là lookup index, CẤM phán quota/2FA/live khi chưa soi UI thật qua CDP/WinRT OCR. Phân tách rạch ròi READY vs WAITING_EXTERNAL. Cấp acc Google thường LIVE trong GPM: (1) Trừ tiktok_accounts và OmniRoute pro; (2) Check Cookies đĩa có SID/HSID/SSID còn hạn; (3) Mở GPM CDP myaccount.google.com xác nhận không bị redirect v3/signin/rejected.
