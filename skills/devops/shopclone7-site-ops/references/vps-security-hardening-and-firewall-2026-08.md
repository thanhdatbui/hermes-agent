# VPS Security Hardening & Firewall Runbook (SHOPCLONE7 / doravo.net)

Date: 2026-08-28  
Host: DigitalOcean SGP1 (152.42.187.200)

## 1. Nginx Baseline Security Headers & HSTS (OWASP)

File: `/etc/nginx/sites-available/doravo.net.conf` (Server block SSL 443)  
Backup: `/root/security-backups/nginx_20260828/doravo.net.conf.bak` (mode 600)

```nginx
# Baseline Security Headers & HSTS (OWASP Recommended)
add_header Strict-Transport-Security "max-age=31536000" always;
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "0" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;
```

- **Validation:** `nginx -t && systemctl reload nginx`
- **Verification:** `curl -sS -D - -o /dev/null https://doravo.net/` -> HTTP 200 + 6 headers present.

## 2. Fail2ban SSH Protection

File: `/etc/fail2ban/jail.d/sshd-hardening.local` (mode 644)

```ini
[DEFAULT]
bantime = 1h
findtime = 10m
maxretry = 5
banaction = ufw

[sshd]
enabled = true
port = 22
backend = systemd
```

- **Validation:** `fail2ban-client -t`
- **Service:** `systemctl enable fail2ban && systemctl restart fail2ban`
- **Verification:** `fail2ban-client ping` -> `Server replied: pong`, `fail2ban-client status sshd`.
- **Action:** Automatically detects brute force from journal and injects `REJECT` rules into UFW.

## 3. UFW Strict Firewall with Anti-Lockout Safety Timer

Backup: `/root/security-backups/ufw_20260828/`

1. **Transient Safety Timer (Fail-safe):**
   ```bash
   systemd-run --unit=ufw-safety-rollback --on-active=5m --timer-property=AccuracySec=1s /usr/sbin/ufw disable
   ```
2. **Apply Strict Rules:**
   ```bash
   ufw --force reset
   ufw default deny incoming
   ufw default allow outgoing
   ufw allow 22/tcp comment "SSH Key Access"
   ufw allow 80/tcp comment "HTTP Web"
   ufw allow 443/tcp comment "HTTPS Web"
   ufw --force enable
   ```
3. **Independent Client Verification:**
   From dev machine: `ssh -p 22 -i ~/.ssh/doravo_deploy -o BatchMode=yes root@152.42.187.200 'echo SSH_OK'`
4. **Cancel Safety Timer once Verified:**
   ```bash
   systemctl stop ufw-safety-rollback.timer
   ```

## 4. Cron Key Log Redaction Verification

Nginx block:
```nginx
location ^~ /cron/ {
    access_log off;
    location ~ \.php$ {
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:/run/php/php7.4-fpm.sock;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
    }
}
```
- **Canary test:** `curl -sS "https://doravo.net/cron/cron.php?key=canary_test" >/dev/null`
- **Verify:** `grep -F "canary_test" /var/www/shopclone7/logs/nginx-access.log` returns empty.
