# VPS Outbound Blackhole Triage & DDoS Rootkit Forensics

## Context & Problem Anatomy
When an e-commerce, scraper, or cron-dependent web application (e.g., Shopclone7, WordPress, custom scrapers) suddenly stops synchronizing stock/prices or reports "Mất kết nối đến kho hàng (HTTP 0)" while inbound HTTP/HTTPS traffic still works normally:
1. **Misconception:** The operator or client often suspects a recent application-level change (e.g., disabling a Telegram bot, pausing a cron job, or modifying configuration).
2. **Reality:** The cloud provider (DigitalOcean, AWS, Hetzner, Linode) has placed an outbound traffic blackhole/isolation filter on the VPS hypervisor after detecting abusive or DDoS traffic from the droplet.

## Forensic Sequence (O(1) Root-Cause Discovery)

### 1. Test Outbound Connectivity vs Inbound
- Inbound: `curl -I https://yourdomain.com` -> 200 OK (inbound traffic passes).
- DNS / Ping: `ping -c 2 8.8.8.8` -> 0% packet loss (ICMP passes).
- Outbound TCP 443 / 80: `curl -Iv --connect-timeout 5 https://google.com` -> `Connection timed out` (Outbound TCP dropped).
- When outbound TCP times out across ALL external domains, check account email immediately for Cloud Provider Abuse notifications (`Droplet Detected Sending Potentially Malicious Traffic` / `DDoS attack participation`).

### 2. Spotting In-Memory Linux Rootkits & DDoS Botnets
Attackers frequently mask malicious processes using common system utility names or high-throughput scanners:
```bash
# Check top CPU consumers:
ps aux --sort=-%cpu | head -n 15

# Look for suspicious binaries in volatile/world-writable mounts:
ls -la /tmp /var/tmp /dev/shm /mnt

# Check process cwd and executable symlinks for running high-CPU PIDs:
ls -l /proc/<PID>/cwd /proc/<PID>/exe
```

**Common Red Flags:**
- High-rate scanners: `./m -iL ranges.lst --rate 80000` (masscan / syn flood).
- Fake system binaries: `/bin/tail`, `/sbin/fsck.ext2`, `/usr/bin/nawk`, `/usr/bin/mysqlimport` running continuously as `root` with accumulated CPU time.
- Malware staging directories: `/mnt/ban2/`, `/dev/shm/ddos`, `/var/tmp/fld`.

### 3. Attack Vector Forensics
Check for common configuration weaknesses:
```bash
# SSH Password Authentication check:
grep -ri "PasswordAuthentication" /etc/ssh/
# Look out for cloud-init overriding sshd:
# /etc/ssh/sshd_config.d/50-cloud-init.conf: PasswordAuthentication yes
```
- If `PasswordAuthentication yes` is enabled, brute-force attacks on port 22 or password leaks grant root shell directly.
- Vulnerable exposed proxy daemons (e.g., unauthenticated or vulnerable Tinyproxy versions like CVE-2023-49606) can allow remote exploitation.

### 4. Database Integrity Verification (Business & Financial State)
- DDoS / Reflector botnets are strictly hardware/bandwidth parasitics; they rarely tamper with PHP or MySQL application tables.
- Verify financial ledger (`dongtien` / orders):
  ```sql
  SELECT * FROM dongtien ORDER BY id DESC LIMIT 10;
  SELECT count(*) FROM product_order WHERE created_at >= CURDATE() - INTERVAL 3 DAY;
  ```
- Confirm database state is intact to validate that existing text backups (.sql) are clean and uncorrupted.

## Remediation Invariants (Fail-Closed)
1. **Never attempt in-place surgical cleanup on root-compromised servers:**
   - Rootkits modify core libraries, inject kernel modules, and hide secondary cron backdoors. Manual file deletion or `kill -9` will leave persistence mechanisms intact.
2. **Clean Rebuild Protocol:**
   - Rely on off-server backups (database dumps, Nginx configuration, uploaded assets) stored on cloud/OneDrive.
   - Destroy the compromised droplet/VPS completely.
   - Spin up a fresh OS instance.
   - Enforce SSH key-only authentication immediately (`PasswordAuthentication no` in `/etc/ssh/sshd_config` and `/etc/ssh/sshd_config.d/`).
   - Restore application code and database from the verified backup.
3. **Hardware Right-Sizing & Provider Optimization:**
   - Lightweight PHP/MySQL shops and scrapers typically consume < 700MB RAM, < 1% CPU, and < 1GB disk under normal load.
   - High-tier VPS ($12/mo for 2GB RAM / 50GB NVMe) are often 70-80% idle. Migrating to $4-$6/mo VPS instances (Hetzner, Vultr, Linode) reduces operational overhead without degrading performance.
