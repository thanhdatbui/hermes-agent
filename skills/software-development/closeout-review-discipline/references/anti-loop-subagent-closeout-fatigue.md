# Chống bẫy loop subagent kéo dài hàng giờ trong pha Closeout (Anti Closeout-Loop Fatigue)

## Hiện tượng & Nguyên nhân gốc (Root Cause)
- **Bẫy đuổi điểm Reviewer (Score-Chasing Trap):**
  Trong pha đóng phiên (`closeout_gate.py`), logic cốt lõi đã hoàn thành và toàn bộ test suite đã xanh, nhưng Reviewer chấm điểm cận biên (82–84/100, thiếu 1-3 điểm để chạm 85).
  Coordinator rơi vào vòng lặp mù quáng: đọc từng finding phụ của Reviewer -> dùng `delegate_task` spawn worker (`ag-gemini-pool-3` / `haiku_worker`) bổ sung test -> test xanh -> chạy lại gate -> Reviewer tiếp tục vạch lá tìm sâu -> lại spawn tiếp worker.
- **Hậu quả:** 5-7 lượt dispatch kéo dài từ 2-3 tiếng đồng hồ, đóng băng hoàn toàn tiến độ, biến một task đã xong thành một cuộc tra tấn kéo dài và khiến User cực kỳ ức chế.
- **Vi phạm quy tắc Hand-off:**
  Khi Gate đã phát cờ `REVIEWER_HANDOFF_TRIGGERED: 4 consecutive rejections reached... Coordinator/Worker/Sol Repair MUST STOP guessing/repairing and hand the keyboard to the Reviewer (Claude CLI)`, Coordinator vẫn tiếp tục vi phạm bằng cách spawn thêm leaf subagents.

## Kỷ luật bắt buộc (Mandatory Rules)

1. **Giới hạn cứng số vòng lặp Remediation trong Closeout:**
   - Tối đa **2 vòng remediation** do Coordinator điều phối trong pha Closeout.
   - Nếu sau 2 lần chạy mà điểm vẫn dao động ở ngưỡng 80-84đ và core test pass 100%: **DỪNG NGAY việc spawn worker subagent.**

2. **Tuyệt đối tuân thủ cờ REVIEWER_HANDOFF_TRIGGERED:**
   - Khi Gate báo cờ Handoff (đã trượt 3-4 lần liên tiếp trên cùng scope_hash):
     **CẤM TUYỆT ĐỐI Coordinator tiếp tục dùng `delegate_task` để spawn subagent.**
     Hành động này bị coi là chống lệnh điều phối và gây lãng phí tài nguyên nghiêm trọng.

3. **Nguyên tắc 80/20 & Tôn trọng lệnh User:**
   - Khi User ra lệnh dứt khoát ("dừng lại", "push cho tao", "chốt phiên"), dừng ngay mọi subagent/process nền, không cố vớt vát thêm bất kỳ test case nào nữa.
   - Kiểm tra commit SHA và trạng thái remote: nếu tree đã sạch và remote đã up-to-date, báo cáo dứt điểm ngay lập tức.
