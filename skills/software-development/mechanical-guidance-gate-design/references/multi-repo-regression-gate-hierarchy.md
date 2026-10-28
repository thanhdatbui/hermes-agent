# Multi-Repo Protection Regression Gate Architecture

## 1. Problem Statement: Cross-Repo False Positives
When managing invariant enforcement across multi-repository workspaces, evaluating all rules on any commit causes **Cross-Repo False Positives (Leaky Abstraction)**.
- *Example:* Editing a desktop/CDP automation project gets blocked by mobile device timing thresholds, or an agent modifying browser flows receives irrevelant hardware triage guidance.

## 2. 3-Tier Invariant Hierarchy

To eliminate cross-repo interference, Protection Regression Gates must be structured into three distinct tiers:

### Tier 0: Global Invariants (`repos: ["*"]`, `paths: ["*"]`)
Rules that protect host machine integrity, event loop stability, and gateway architecture. A violation in ANY repository is immediately blocked:
- Broad root-level filesystem traversals that exhaust memory or freeze event loops.
- Deprecated UI dump utilities on legacy mobile devices that trigger OOM exits.
- Terminal stdout flooding (e.g. giant payloads/base64 strings).
- Unsupported network proxy protocol schemes in messaging gateway configuration.

### Tier 1: Repo-Scoped Invariants (`repos: ["<repo_name>"]`)
Rules that apply strictly to the repository owning that domain logic:
- **Phone Farm Automation:** Device connection timing floors, friend follow limits, and avoiding global rest-day overrides.
- **Desktop / CDP Automation (GPM):** Initial stage ordering, ensuring reg scripts return non-zero exit codes on failure, prohibiting direct IP fallbacks when proxies drop, and worker concurrency limits.
- **Core Tooling:** Subagent execution timeout floors.

### Tier 2: Path-Level Invariants (`paths: ["<path_glob>"]`)
Narrowing rule execution within a repo to only modified files that actually contain the protected function or logic.

## 3. Storage Architecture: Canonical Base vs Repo-Local Rules

### Centralized Base (`tools/guardgate/rules.json`)
- Acts as the Single Source of Truth for Global Invariants (Tier 0) only (e.g., broad disk scan, uiautomator dump, domain in Android proxy, socks5h scheme, bulk device lock reservation, base64 in stdout, rogue wifi SSID).
- CẤM nhồi nhét rule đặc thù của từng repo con vào file base này để tránh biến file thành "nồi lẩu thập cẩm" và gây ô nhiễm context.

### Repo-Local Extension (`<repo>/rules.json`)
- Repositories define domain-specific rules locally in `<repo>/rules.json` (e.g., `GPM auto/rules.json`, `tiktok-luot nuoi acc/rules.json`, `tools/rules.json`).
- Sửa code repo nào CHỈ chịu trách nhiệm trước rule của chính repo đó + các luật sống còn toàn farm.
- The gate runner automatically discovers and merges repo-local rules when evaluating diffs against a specific target repo:
  ```python
  if repo:
      repo_rules_file = Path(repo) / "rules.json"
      if repo_rules_file.is_file() and repo_rules_file.resolve() != RULES_FILE.resolve():
          try:
              with open(repo_rules_file, "r", encoding="utf-8") as rf:
                  repo_rules = json.load(rf)
                  if isinstance(repo_rules, list):
                      existing_ids = {r.get("id") for r in rules}
                      for rr in repo_rules:
                          if rr.get("id") not in existing_ids:
                              rules.append(rr)
                              existing_ids.add(rr.get("id"))
          except Exception:
              pass
  ```
- **ID Deduplication Invariant:** Merging MUST deduplicate rule IDs (`rr.get('id') not in existing_ids`) to prevent `GateConfigurationError("rule ids must be unique")` if a repo rule shares an identifier with canonical rules.
- **Cross-Repo Verification Contract:** Verification suites must include cross-repo assertions proving:
  1. Target repo diff triggers target repo-local rule (`DENY`).
  2. Non-target repo diff with same pattern is ignored (`ALLOW`).
  3. Global invariant diff triggers `DENY` regardless of `--repo`.

## 4. Separation of Concerns: Pre-Execution Interceptors vs Commit Gates

- **Pre-execution interceptors (Runtime layer):** Intercept command executions on the live terminal/session before commands run to prevent immediate system disruption.
- **Regression Gates (Commit layer):** Analyze git diffs at closeout/push time to prevent improper patterns from entering version control history.
- The two layers operate at different lifecycle moments and complement each other.

## 5. Terminology Pitfall: `guardgate` vs `infra_regression_gate.py`
- **`guardgate` (`D:/Taadaa/tools/guardgate`)**: CHÍNH LÀ Protection Regression Gate cho code & script của toàn bộ repositories. Tích hợp trực tiếp tại **Step 2.5 của `closeout_gate.py`** (`from guardgate.runner import check_diff`). Soi từng dòng thêm mới (`git diff`) đối chiếu với `rules.json` (toàn farm) và `<repo>/rules.json` (từng repo) để chặn đứng mọi mâu thuẫn/hồi quy trước khi commit.
- **`infra_regression_gate.py` (`D:/Taadaa/tools/infra_regression_gate.py`)**: CHỈ là bộ kiểm tra tĩnh 4 file cấu hình hạ tầng của riêng Hermes & OmniRoute (`config.yaml`, `server.env`, `omniroute_watchdog.ps1`, `cleanup_omniroute_db.py`). TUYỆT ĐỐI không nhầm lẫn file này thành Protection Regression Gate của các repo code farm.

