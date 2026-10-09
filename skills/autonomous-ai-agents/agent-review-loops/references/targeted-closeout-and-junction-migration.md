# Targeted closeout and junction migration

Use this reference when a repository contains unrelated staged work or when a Windows runtime directory is migrated to a Git source-of-truth.

## Closeout scope preflight

1. Capture the intended target list before running the gate.
2. Check `git diff --cached --name-only` and require an exact set match with `closeout_gate.py --files`. If `staged files != --files targets`, `targeted_candidate` crashes fail-closed with exit code 1.
3. If extras are staged from previous sessions, run a non-destructive mixed reset:
   `git reset HEAD`
   (làm sạch index, giữ nguyên 100% thay đổi working tree). Sau đó chỉ stage đúng exact target list kèm focused tests:
   `git add <target_files...> <test_files...>`
   Re-check `git diff --cached --name-only` trước khi gọi Gate.
4. Do not use `--skip-test`; repo closeout requires executed tests.
5. Run focused tests for every reviewed production file. Source-text contract tests are useful but do not replace offline/runtime-mocked behavior tests.
6. Treat truncation, missing telemetry evidence, and missing runtime evidence as reviewer findings. Keep candidate diff < 60KB to prevent `SolPayloadGuard` truncation from docking score on unobserved lines. Either add a bounded regression test or narrow the review scope; never infer production safety from partial evidence.
7. Close only on `Verdict: APPROVED` and `Overall Score >= 85/100`.
8. **Communication Invariant:** CẤM TUYỆT ĐỐI báo cáo "Đã hoàn tất / An toàn" hay kết thúc phiên khi Closeout Gate trả về `REJECTED` (< 85). Khi Gate trượt, báo cáo trung thực: "Closeout Gate chưa đạt (Điểm X/100, REJECTED)" và nêu rõ các finding cần khắc phục.

## Windows Git source-of-truth migration

For a single-controller Hermes deployment, migrate the complete plugin tree into the Git bundle, preserve a backup of the old AppData directory, and expose the Git tree through an NTFS directory junction (`mklink /J`). The setup script should fail closed if the source bundle is absent and should not overwrite a real destination directory. Verify the junction contract offline and verify the runtime import/readback separately; do not claim migration success from a script that merely exits zero.

## Pitfalls observed

- A successful worker report does not prove the index has the requested staged scope; always inspect the index yourself.
- Repeated closeout runs can review a previous task's staged files unless the index is normalized first.
- A large policy file can be truncated by the reviewer input path; narrow the candidate diff or provide focused evidence rather than treating the partial review as approval.
- Unit tests passing for one test file do not establish regression safety for unrelated watchdog, device, GPM, or S7 flows.
- Saying "done / safe" when a gate scored 76-82/100 breaks trust; treat gate score as the sole authority on readiness.
