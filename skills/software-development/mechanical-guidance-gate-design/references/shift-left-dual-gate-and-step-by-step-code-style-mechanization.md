# Co Gioi Hoa Phong Cach Code & Kien Truc Shift-Left Dual-Gate GuardGate

## 1. Bai Hoc Xuong Mau: Cam Cam Ket Mieng
- Khi User yeu cau phong cach viet code hoac quy tac kien truc, tuyet doi khong dung loi hua hay cam ket suong.
- Moi quy tac bat buoc phai duoc co gioi hoa bang code kiem tra tinh ben trong GuardGate (rules.json, predicates.py, runner.py).

## 2. Invariant Phong Cach Code: Step-by-Step Structure
- Rule ID: `case_invariant_require_step_by_step_structure` (Scope: repos: ["*"], paths: ["*.py"]).
- Nguong kich hoat: Khi git diff them moi tu 15 dong code tro len (da loai tru import, dong trong, comment, docstring).
- Yeu cau bat buoc: Code moi bat buoc phai chua it nhat mot comment/banner dinh danh buoc (# Buoc X: ... / # Step X: ... hoac banner # ===).
- Xu phat: Them >= 15 dong code tran khong phan buoc se bi GuardGate tra ve DENY ngay lap tuc.
- Mandatory Pipeline Steps: Tung repo runner chinh co rule rieng khoa cung danh sach required_steps tuan tu (vd: ["BUOC 1", "BUOC 2", "BUOC 3", "BUOC 4"]).

## 3. Kien Truc Vi Tri Dat GuardGate: Shift-Left Dual-Gate
- Sai lam neu chi dat o Closeout: Thiet hai tren may that da xay ra truoc khi den buoc closeout 30-45 phut.
- Mo hinh 2 Tang:
  * Tang 1: Pre-Apply / Pre-Commit (chan ngay khi sinh diff, truoc khi chay tren thiet bi that).
  * Tang 2: Closeout Gate (giu nguyen tai Step 2.5 closeout_gate.py lam chot chan cuoi truoc khi push).

## 4. Quan Ly Rules Toan Farm
- Moi repo automation bat buoc phai co file rules.json rieng.
- Engine tu dong merge luat chung toan farm voi luat rieng tung repo theo ID deduplication.
