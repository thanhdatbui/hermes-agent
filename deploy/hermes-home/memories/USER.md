Cào/Render: 12 niche hot (rải xen kẽ máy, cấm trùng niche cùng phiên); min 45; 1 wkr.
§
Dọn đĩa: duyệt trước (thư mục corrupt/lỗi xóa ngay), CẤM xóa ngầm.
§
Farm: nick cấm xóa/đè; SoT tiktok_tracker.db; cấm đè ava tay; Canary tự mở app & chuyển nick qua automation_core, cấm gọi user mở tay. Nuôi 4d 3 ca (bỏ ca đêm, idle dập TT & tắt màn 223); Starve 96h. Đổi mail: Hotmail sạch, ưu tiên Graph PC.
§
cấm raw/trace dump hay telemetry JSON ra stdout cron (bắt buộc stderr); chốt phiên bắt buộc push remote thật rồi mới báo DONE;
§
Kibe(1-80) & Admin(201-280) cào nguồn & media độc lập 100% (cấm trùng video, cấm sync chéo Niche/Hashtag). TT v47.0.3; Switcher dock; AP 40m.
§
Ghim video: pin_top_videos.py (Share->Ghim, min 1000 view); DB ko lưu view, đọc live ATX; re-dump sau mỗi lần ghim chống bẫy đảo lưới.
§
Worker: Haiku 5.5 CLI (haiku_worker.py 6-15s O(1)) chính, AG CLI 7 acc Pro dự phòng; đo chất lượng code/diff thật; quota thật qua plan-usage-history.json; Coord giữ Hermes 24/7.
§
Hashtag sync: F_src=(Slot-1)*80+m_idx, SoT 'Hashtag theo Folder'; nick fix tay khóa manual_avatar_protected_folders.json cấm sync đè.
§
Telegram: song song nhiều topic, tự resume turn dở sau boot.
§
Reboot: user lệnh là làm ngay, cấm hỏi lại 'reboot nhé'; tự xóa sentinel flag, stamp preserve_in_flight & shutdown.