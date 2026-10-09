# Advisor Strategy vs Plan/Review: Co Che & Ung Dung Trong Phone Farm

## 1. Ban chat: Advisor Strategy vs Planning vs Review

| Dac tinh | Pre-Plan (Lap ke hoach truoc) | Post-Review (Tham dinh sau) | Advisor Strategy (Co van trong vong lap) |
|---|---|---|---|
| **Thoi diem goi** | Truoc khi bat dau thi cong | Sau khi da sinh artifact / diff | Ngay tai thoi diem Coordinator gap quyet dinh kho |
| **Boi canh (Context)** | Tong quan yeu cau, tai lieu, kien truc | Git diff, commit, log test, telemetry | Trajectory hien tai (lenh vua chay, loi vua gap, 2-3 nga re) |
| **Quyen han cua Model manh** | Dua blueprint, phan ra task | Phan quyet APPROVED / REJECT | Read-only guidance (chon nga re, canh bao ranh gioi, invariant) |
| **Hanh dong sau do** | Coordinator / Worker thuc thi theo plan | Worker sua loi neu REJECT; dong phien neu APPROVED | Coordinator tu giu quyen dieu phoi va tiep tuc tool loop ngay |
| **Muc dich chinh** | Tranh lac huong task phuc tap multi-file | Bao ve chat luong truoc khi release/commit | Quyet dinh chuan xac tai cho voi chi phi re hon chay model manh toan phien |

---

## 2. Vi sao goi "Model manh ra plan/review" khac voi "Advisor"?

- **Plan/Review la Batch/Phase Gate:** Duoc thiet ke nhu tram kiem soat co dinh (truoc cong hoac sau cong). Coordinator phai goi context thanh mot prompt rieng biet, goi tien trinh con (nhu `sol_planner.py` hoac `closeout_gate.py`), cho doi va nhan ve mot tai lieu hoan chinh.
- **Advisor la Dynamic In-Loop Escalation:** Coordinator (model tiet kiem, phan xa nhanh nhu Gemini/Sonnet) tu lai toan bo luong cong viec. Khi gap mot tinh huong khong chac chan (vi du: cookie het han hay bi Cloudflare chan? Nen clear session hay giu nguyen de tai dung?), no goi Model manh (Opus/Sol) nhu mot ham tu van cuc bo O(1) de xin chi dan chien thuat roi tu lam tiep.

---

## 3. Khao sat thuc te Phone Farm (Log Session Audit)

Qua khao sat cac phien lam viec thuc te cua Taadaa Phone Farm:
1. **Tiered Workflow 2.0 / 3.0:** Coordinator (Gemini) tu lam T0 (doc log, inspect) va tu lap Patch Contract O(1) cho Worker.
2. **Sol Pre-Plan:** Chi kich hoat theo trigger rui ro cao (dung guard/hook, >= 3 files, deadlock). Day la **Pre-Plan**, khong phai Advisor.
3. **Closeout Gate:** Chay `closeout_gate.py` de cham diem >= 85/100 truoc khi push. Day la **Post-Review**.
3. **Hien trang (đã cập nhật):** Claude Code v2.1.281 có Advisor native trong TUI qua `/advisor <model|off>` và lưu `advisorModel`; cặp khuyến nghị là Main Sonnet 5 + Advisor Opus 5.5. Hermes Phone Farm vẫn chưa có `advisor_consult` native tương đương, nên các lane Advisor nội bộ vẫn phải dùng CLI/script gate hoặc cơ chế tích hợp riêng.

---

## 4. Thiet ke co che Advisor cho Hermes Coordinator

De hien thuc hoa Advisor Strategy trong ha tang Hermes ma khong lam phinh context hay hao phi quota:

### A. Contract cua Advisor Tool (`advisor_consult`)
- **Input:**
  - `question`: Cau hoi chien thuat cu the (khong hoi chung chung "hay lam task nay").
  - `evidence`: Du lieu hien truong O(1) (log trich xuat, DOM/XML snippet, ma loi HTTP).
  - `candidate_actions`: 2-3 phuong an Coordinator dang can nhac.
  - `hard_constraints`: Cac Invariant tuyet doi (khong mat nick, khong quet dia, khong dung guard).
- **Quy tac thuc thi:**
  - Advisor model: Chay read-only qua OmniRoute HTTP (`plan-review` hoac `ag-claude-pool` / Opus).
  - CAM Advisor goi tool, CAM dung ADB, CAM sua file.
  - Tran goi cung: Toi da 1 lan/case thuong, toi da 2 lan/case cuc kho.

### B. Output mong muon
```json
{
  "selected_action": "QUARANTINE_AND_REFRESH_SESSION",
  "rationale": "DOM hien thi session expired nhung cookie con han, probe API truoc khi xoa de tranh mat nick.",
  "forbidden_actions": ["pm clear", "bulk_relogin"],
  "verification_step": "Chay probe 1+1 tren tab an danh"
}
```
Coordinator nhan ket qua, tiep tuc tu dieu phoi Worker thi cong va kiem chung theo gate tieu chuan.
