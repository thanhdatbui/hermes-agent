# Shared Host Dependency Audit & Backup Parity Protocol

**Date:** 2026-10-26  
**Context:** Auditing dependencies and verifying backup readiness on shared, borrowed, or external cloud VPS hosts (e.g. `doravo.net` / `152.42.187.200`) before handover, cancellation, or OS reinstallation.

---

## 1. The Decommission / Dependency Audit Taxonomy

When an operator asks whether internal operations, farm devices, or local tools still rely on an external or shared VPS (*"Vps này mình có dùng gì trên đó không... trừ web của ông anh"*), systematically audit three distinct vectors before confirming zero-dependency:

### Vector 1: Inbound / Outbound Network Routing (Tunnels & Proxies)
* **Historical Pattern:** External cloud VPS nodes in low-latency hubs (e.g. DigitalOcean SGP1 Singapore) are frequently drafted as emergency proxy hops (e.g. `Tinyproxy` on port `18888`) to bypass domestic ISP packet inspection or undersea cable drops for Telegram bot long-polling (`TELEGRAM_PROXY`).
* **Audit Check:**
  1. Inspect local environment configs (`.env`, `config.yaml`, gateway configs) for references to the VPS public IP or proxy port.
  2. Confirm whether traffic has been decoupled to a local multi-ISP failover mechanism (e.g. `TelegramMultiISPTransport` bouncing between local Viettel proxy `:10001` and FPT direct `:10002`).
  3. Verify that zero local processes, LLM routers, or scrapers are routing traffic through the remote proxy.

### Vector 2: Client-Facing Integrations vs Internal Farm Infrastructure
* **Separation of Concerns:** External cloud servers often host client/partner-facing integrations (e.g. `doravo-mcp` running on internal port `8100`, reverse-proxied via Nginx at `https://domain.com/mcp` for ChatGPT mobile connectors).
* **The Distinction:**
  * **Client Surface:** If the host is shut down, external clients (e.g. anh Nguyên using ChatGPT to inspect medical tenders) lose access to the connector URL.
  * **Internal Farm Surface:** The bidding crawler, database scraper, and analysis engine run entirely on local host machines (`D:/Taadaa`). The death of the VPS does NOT interrupt local farm automation, device feeds, or scraping schedules.
* **Communication Rule:** Clearly report this boundary to the operator: internal farm/bot tools are 100% immune, while partner-facing features hosted on that domain will go dark if the VPS is terminated.

### Vector 3: Shared Bot Identities, Crontabs & Telemetry Hooks
* **Shared Bot Identity Collision:** Multiple scripts across different domains (e.g. ecommerce stock checklive vs public tender watchdog) often share a single Telegram bot token.
* **Audit Check:**
  1. Check remote crontab (`crontab -l`) and systemd timers on the VPS.
  2. Confirm that automated database alerts (`telegram_status = '0'`) and push cronjobs have been paused or decommissioned.
  3. Ensure no dangling webhooks or callback URLs point to the target VPS.

---

## 2. The "Code in Git != Live Database" Backup Hazard

### The Failure Mode
Operators commonly ask: *"Backup hết hạ tầng của X vào chỗ nào chưa?"*  
A superficial agent checks `git status` on the local repository (e.g. `D:/Taadaa/site ban hang clone`), sees clean commits pushed to GitHub (`origin/main`), and falsely reports: *"Đã backup hết 100% rồi."*

This is a **catastrophic false assurance**:
* **Git Repository & Deploy Runbooks:** Only capture the static code (`SHOPCLONE7/`, `mcp_server/`), deployment scripts (`prepare_vps_ubuntu.sh`), Nginx vhost templates, and systemd units.
* **Live Transactional State:** Customer user tables, order histories, purchase logs, top-up balances, supplier API pricing overrides, and audit trails accumulate **exclusively in the active MariaDB/MySQL database** on the VPS.
* **The Reality:** A post-install database snapshot from initial deployment (e.g. July 2026) is completely stale. Months of transactional data will be permanently destroyed if the server is wiped.

### Strict Verification Protocol Before Decommissioning
1. **Differentiate Code vs Data explicitly:**
   * Report static codebase status: local path + GitHub remote repository.
   * Report database state: location of latest dump, date/time of last export, and whether live records are synced.
2. **Execute On-Demand Live Dump Before Termination:**
   If the operator plans to release or wipe the host, immediately pull a fresh transactional dump:
   ```bash
   mysqldump --single-transaction --routines --triggers --quick <database_name> | gzip > db_backup_$(date +%Y%m%d_%H%M%S).sql.gz
   ```
   SFTP the compressed archive to safe local storage (`D:/Taadaa/<repo>/backups/`) and confirm non-zero file size before approving host decommission.
