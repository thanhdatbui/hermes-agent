# Kien Truc Tu Dong Bao Toan & Phuc Hoi Session Hermes Sau Reboot (Zero-Chat Auto-Resume)

## 1. Van De Thuc Te Cua User
- User lam viec tren Telegram voi nhieu topics/sessions dong thoi (moi topic la 1 bug hoac task xu ly rieng tren farm).
- Khi host PC reboot (theo lich 11:35 truoc ca trua hoac user restart thu cong):
  * Tat ca cac topic dang fix bug do dang bi ngat dot ngot.
  * Khi Gateway online lai, cac topic deu im lang hoan toan.
  * User rat ngai va mat cong phai bam vao tung topic (5–10 topics) go "tiep tuc di", "fix tiep di".

## 2. 3 Nut That Ky Thuat Khien Hermes Khong Tu Chay Tiep
1. **120s Timeout Lệch Pha Phan Cung:**
   - Ham `suspend_recently_active(max_age_seconds: int = 120)` trong `gateway/session.py` fix cung 120 giay (2 phut).
   - Bo mach chu Server Dual Xeon X99 khi POST BIOS, kiem tra RAM, boot Windows mat 130–150 giay.
   - Den khi Gateway khoi dong xong, moi session truoc do deu da qua 120 giay nen bi bo qua sach se (0 candidate).
2. **System Note Mac Dinh Bi Dong (Passive Recovery Prompt):**
   - Khi Gateway tu phuc hoi session voi event rong (`event.text == ""`), system note mac dinh (`_resume_guidance`) lai dan model:
     *"Report to the user that the session was restored successfully and ask what they would like to do next. Do NOT re-execute old tool calls — skip any unfinished work from the conversation history."*
   - Model doc huong dan nay chi chao hoi suong ma KHONG tiep tuc xu ly code hay fix bug.
3. **Thieu Danh Dau Tien Tram (Pre-Reboot Stamping):**
   - Script reboot `farm_preflight_daily_reset.py` goi thang `shutdown /r /t 5` ma chua danh dau bao toan trang thai cho cac session dang chay.

## 3. Giai Phap Toan Dien 3 Tang
- **Tang 1 (Tien tram truoc Reboot):**
  Trong `farm_preflight_daily_reset.py`, truoc khi reboot, quet database session SQLite tim cac topic Telegram chua ket thuc (`ended_at IS NULL`) co `last_role IN ('user', 'tool')` (turn dang chay do dang).
  Cap nhat vao bang dinh tuyen `gateway_routing`:
  `resume_pending = True`, `resume_reason = "restart_interrupted"`, `last_resume_marked_at = now`.
  Xoa `.clean_shutdown` de Gateway khong bo qua buoc khoi phuc.
- **Tang 2 (Mo rong cua so phuc hoi):**
  Nang `max_age_seconds` tu 120s len 1800s (30 phut) trong `gateway/session.py` de thich ung chu ky reboot server X99.
- **Tang 3 (Chuyen huong System Prompt sang Chu Dong):**
  Khi resume, dan model:
  *"Kiem tra lai hien truong trang thai thiet bi/farm sau reboot va chu dong tiep tuc thuc thi de hoan thanh dut diem task dang do ve DONE hoac BLOCKED kem bang chung thuc te."*

## 4. Phuong An Dieu Phoi 1 Lenh Tong (One-Click Fallback)
Khi chua co ban va ma nguon Gateway, phuong an thuc dung nhat la:
- User chi can nhan dung 1 cau tai 1 topic tong: *"Tiep tuc cac session dang do truoc reboot di"*.
- Coordinator doc database session, phan loai cac topic bi dut mid-flight (`last_role IN ('user', 'tool')`).
- Dispatch cac worker song song qua `delegate_task` xu ly dut diem tung task.
- Ban ket qua nghiem thu vao tung topic tuong ung qua `hermes send --to telegram:<chat_id>:<thread_id>`.
