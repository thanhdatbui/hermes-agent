# Kien Truc Co Hoc 3 Tang: Hook vs Guard vs Gate & Quy Chuan Kiem Tra Xung Dot (18/10/2026)

## 1. Phan Dinh Ban Chat: Hook vs Guard vs Gate (The Kieng 3 Chan Co Hoc)

Khi thiet ke he thong dieu phoi va bao ve farm, tang co hoc hoan chinh bat buoc phai co du 3 thanh phan:

```text
       [TOOL CALL CUA AGENT / RUNTIME EVENT]
                         │
                         ▼
┌──────────────────────────────────────────────────┐
│  1. HOOK (Cam bien don chan / Event Interceptor) │  <-- "Cong quet an ninh"
└────────────────────────┬─────────────────────────┘
                         ▼
┌──────────────────────────────────────────────────┐
│  2. GUARD (Luat cam co hoc / Binary Filter)      │  <-- "Quy dinh cam vat the nguy hiem"
└────────────────────────┬─────────────────────────┘
                         ▼
┌──────────────────────────────────────────────────┐
│  3. GATE (Cong kiem chung / Evidence Checkpoint) │  <-- "The tu quet qua cua / Nghiem thu"
└────────────────────────┬─────────────────────────┘
                         ▼
                 [THUC THI TREN FARM]
```

### Chi tiet 3 tang:

1. **HOOK (Cam bien don chan - Event Interceptor):**
   - **Ban chat:** La co che moc vao vong doi runtime cua he thong (`PreToolUse`, `PostToolUse`, `PreCommit`, `SessionStart`).
   - **Nhiem vu:** Lang nghe va chan bat goi tin tool call ngay truoc khi lenh cham toi he dieu hanh.
   - **Dac tinh:** Khong tu dua ra phan quyet nghiep vu; no chi trich xuat tham so (`cmd`, `path`, `timeout`, `args`) va chuyen giao cho Guard.

2. **GUARD (Luat cam co hoc - Binary Policy Enforcer):**
   - **Ban chat:** La logic kiem tra nam ben trong Hook hoac Wrapper, hoat dong theo nguyen ly **CAM DOAN TUYET DOI (Default-Deny)**.
   - **Nhiem vu:** Chem chet ngay lap tuc cac hanh vi sai trai, nguy hiem hoac pha hoai ma khong can hoi:
     - Broad scan guard: Chem lenh quet dia dien rong (`os.walk`, `grep -r`), chem lenh foreground co `timeout > 60s`.
     - Android proxy guard: Chem lenh gan domain ngoai lam proxy, chi nhan LAN IP RFC1918 `192.168.110.2:<port>`.
     - Device bulkhead & Hard Gate #5: Chem lenh ADB tran thieu `-s <serial>` hoac chua giu device lock.
     - Role model lock: Chem lenh override Sonnet khi role la `worker` (Exit code 2 `[ROLE_MODEL_MISMATCH]`).

3. **GATE (Cong kiem chung / Tram nghiem thu - Evidence Checkpoint):**
   - **Ban chat:** Khong chi cam doan thu dong ma la **dieu kien Can & Du de duoc di tiep** vao giai doan sau.
   - **Nhiem vu:** Muon qua Gate bat buoc phai nop bang chung that (Evidence-backed verification):
     - `Canary Gate`: Phai chay test xanh tren 1 may that, co log va anh chup man hinh xac thuc moi duoc rollout toan farm.
     - `Closeout Gate`: Phai co phan quyet `Verdict: APPROVED` diem >= 85/100 tu Sol Auditor moi duoc phep push chot phien.
     - `Farm Network Gate`: Phai thoa man lien hoan L2 -> L3 -> L4 moi duoc coi la mang thong; loi tang duoi cam sua tang tren.

- **Hook** bao dam khong co ke ho lot lenh ngoai kiem soat.
- **Guard** loai bo ngay lap tuc 100% cac thao tac nguy hiem.
- **Gate** bao dam chat luong dau ra, chong tinh trang Agent "bao cao ao / xong mom" ma khong co artifact that.

---

## 2. Quy Chuan Kiem Tra Xung Dot 2 Tang (Two-Tier Conflict Verification Protocol)

Tu nay, truoc khi bat ky file Gate, Guard, hay Hook moi nao duoc thiet ke hoac dua vao code, Coordinator **BAT BUOC** phai chay qua 2 checklist doi soat xung dot:

### Checklist Tang 1: Doi soat voi cac Guard hien huu
- [ ] **Android Proxy:** Co vo tinh nap domain ngoai vao Android proxy khong? (Bat buoc RFC1918 LAN `192.168.110.2`).
- [ ] **Windows Console Safety:** Moi subprocess goi tren Windows co gan `creationflags=0x08000000` (`CREATE_NO_WINDOW`) khong?
- [ ] **Foreground Timeout Guard:** Lenh co timeout > 60s tren foreground khong? (Neu chay tac vu nang > 50s, bat buoc `background=True, notify_on_complete=True`).
- [ ] **Device Bulkhead:** Moi lenh ADB co chi dinh ro `-s <serial>` va boc trong `operator_device_lock` khong?
- [ ] **Quet dia dien rong:** Co chua `os.walk`, `rglob`, `grep -r`, `find` quet tren root cam khong?
- [ ] **Vung cam Guard:** Co dung cham, sua doi hoac xoa code trong thu muc guard noi bo cua he thong khong?

### Checklist Tang 2: Doi soat voi cac Invariants Van Hanh Farm cua Operator
- [ ] **Bao ve tien trinh nuoi (25 workers):** Module co co che Idempotent (`NOOP_HEALTHY`) de khong ngat ket noi cua nick dang chay khong?
- [ ] **Ngoai le may dac thu:** Da xu ly cac ngoai le cung chua? (Vi du: M67 va M69 la Direct, proxy `:0`, cam ep qua Sing-box).
- [ ] **Cuu ho khan cap:** Co ho tro co cuong che `force_preempt=True` trong `operator_device_lock` de cuu may khi bi ket lock cu khong?
- [ ] **Khong cuop focus:** Script co am tham bat cua so lam gian doan may tinh cua User (TFT/War3) khong?
- [ ] **Kiem thu offline:** Bo test suite di kem co chay 100% mocked offline va hoan tat duoi 30 giay khong?

---

## 3. Triet Tieu Benh "Xin Loi Mom" Khi Dieu Phoi Claude CLI

Khi lam viec voi Claude Code CLI:
1. **Khoa cung vai tro bang code:**
   - Worker = Haiku 5.5 (`claude-haiku-5-5`) hoac Agy CLI (`ag_cli.py fix`). Cam tuyet doi Sonnet lam tho go code.
   - Planner / Reviewer = Sonnet 5.5 (`claude-sonnet-5-5`), chi doc va tham dinh.
   - Moi no luc override Sonnet vao role worker deu bi `claude_worker.py` nem loi `[ROLE_MODEL_MISMATCH]` va exit 2 ngay lap tuc.
2. **Quy tac Background Bat Buoc:**
   - Moi lenh goi Claude CLI deu can tu 25s-50s. BAT BUOC goi bang `terminal(background=True, notify_on_complete=True, timeout=120..180)`.
   - Cam tuyet doi goi foreground voi `timeout > 60s` dan toi bi `GUARD_FOREGROUND_TIMEOUT_EXCEEDED` quat chet lap di lap lai.
