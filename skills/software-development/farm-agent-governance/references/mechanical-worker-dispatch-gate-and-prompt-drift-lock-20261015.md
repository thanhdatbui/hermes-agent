# Mechanical Worker Dispatch Gate & Prompt Drift Lockout (2026-10-15)

## 1. Ban chat su co
Operator yeu cau thi cong sua code routine bat buoc dung haiku_worker (Claude Haiku 5.5 CLI O(1), 6-15s).
Tuy nhien khi Operator ra lenh "R lam di", Coordinator van goi delegate_task (subagent omni-worker / Gemini pool) ton 211 giay (>3.5 phut) lam loang context.
Operator chan chinh: Can khoa cung o tang gate/setting thay vi chi dua vao prompt.

## 2. Phan tich kien truc
- delegate_task la tool noi bo cua Hermes Agent tro toi HTTP endpoint tren OmniRoute.
- haiku_worker la script doc lap boc claude -p chay qua terminal.
- Prompt-based discipline luon that bai trong dai han do Prompt Drift, Context Compaction, va contradictory directives trong System Prompt cu.
- Giai phap duy nhat: Khoa cung bang Mechanical Gate fail-closed tai pre-tool hook dispatch contract.

## 3. Thiet ke & Phe duyet tu Claude CLI
Claude CLI ban hanh phan quyet: VERDICT: APPROVED cho co che Hard Block:
- Khi delegate_task co intent sua code (is_code_edit):
  Neu khong co co ngoai le (ALLOW_SUBAGENT_CODE_EDIT hoac OVERRIDE_SUBAGENT_DISPATCH):
  Lap tuc BLOCK va yeu cau dung haiku_worker.
- Task INVESTIGATE read-only (<= 5 calls) van duoc phep de giu sach context Coordinator.

## 4. Kiem thu nghiem thu
Bo test test_guard_dispatch_contract da duoc bo sung test case cho co che moi va dat 100% PASS (8 passed in 1.65s).
