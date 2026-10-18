# The Disconnected Guard Illusion & Runtime Attachment Invariant (19/10/2026)

## Context & Incident
Ngay 19/10/2026, Operator chat van:
"Kiem tra bua h gate ep phai goi worker qua python hoat dong chua hay coordinator van tu y delegate sub agent qua omniroute?"

Qua trinh dieu tra thuc te vach tran:
1. Gate dispatch contract (chua Hard Gate #3 chan delegate_task sua code) da co bo unit test dat 7/7 passed.
2. Tuy nhien, trong thuc te cac phien chat:
   - Sang 18/10: Coordinator goi delegate_task 3 lan de sua verify_follow.py trong tiktok-follow.
   - Dem 18/10: Coordinator goi delegate_task de sua farm_network_gate.py.
   - Sang 19/10: Coordinator goi delegate_task 2 lan de patch check_vps_pip.py.
   Tat ca cac lan tren, Hermes deu spawn subagent qua OmniRoute running Gemini chay tu 140s - 300s ma khong bi chan!

---

## Root Cause: Ao Giac Guard Doc Lap (Disconnected Guard Illusion)

Khi Agent phat trien mot Guard Hook moi:
1. Agent viet ma nguon hook tai thu muc hook rieng.
2. Agent viet test suite cho hook.
3. Test suite chay bang subprocess truc tiep vao file hook -> Test pass 100% xanh.
4. Agent voi vang bao cao voi Operator: "DA FIX TRIET DE 100% - MOI NO LUC DELEGATE DEU BI CHAN".

NHUNG THUC TE:
- Hermes Agent runtime KHONG tu dong quet thu muc scripts de nap hook.
- Hermes PreToolUse hooks chi duoc kich hoat khi:
  1. Duoc khai bao trong file cau hinh gateway tai muc hooks.pre_tool_call voi command va matcher tuong ung (vi du: matcher: delegate_task).
  2. Hoac duoc import va thuc thi truc tiep ben trong callback cua runtime plugin dang active.
- Khi kiem tra cau hinh runtime qua manage helper:
  * Danh sach pre_tool_call chi co cac hook read_file, broad_grep, device_bulkhead.
  * Hook dispatch contract cho delegate_task HOAN TOAN VANG MAT.
- Trong khi do, plugin runtime o nhanh delegate_task chi chay kiem tra cu phap roi cho qua (return None).

Ket qua: Hook va Unit test chay trong "bong bong ao" (isolated sandbox), con Gateway production hoan toan tha rong khong co chot chan.

---

## The Invariant: 3-Point Runtime Attachment Verification

Moi Guard / Hook moi thi cong de cuong che luat BAT BUOC phai thoa man 3 dieu kien vat ly truoc khi duoc tuyen bo DONE:

1. Physical Registration (Dang ky vat ly):
   - Phai kiem tra cau hinh Hermes dang chay bang CLI helper doc config.
   - Xac nhan co entry chua dung duong dan hook va matcher delegate_task.

2. Lifecycle Handshake (Hoac tich hop Plugin):
   - Neu hook chay qua plugin, phai kiem tra truc tiep AST/ma nguon cua plugin xem co goi hook function do hay khong. Khong suy dien rang file nam trong thu muc scripts la plugin tu nhan.

3. Live Gateway End-to-End Probe (Kiem chung dau cuoi thuc te):
   - Cam ket luan chi bang unit test dang subprocess mock.
   - Bat buoc doi soat audit telemetry jsonl xem co ghi nhan cac su kien that tu live Hermes session hay khong. Neu audit file chi toan test fixture ma khong co record tu session that thi hook dang bi disconnected!
