---
name: php-verification-without-runtime
description: "Verify PHP edits (CMSNT/SHOPCLONE7, legacy PHP) when php CLI is unavailable: brace balance, node --check on rendered embedded JS, content invariants, diff hygiene, ad-hoc verify scripts."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [php, verification, lint, cmsnt, shopclone7, legacy-php, no-runtime, embedded-js]
    related_skills: [systematic-debugging, test-driven-development, code-audit]
---
# PHP Verification Without a PHP Runtime

## Overview

You edited PHP files but there is no `php` CLI on the machine (common on Windows sandboxes/git-bash hosts). You must still produce **honest, mechanical evidence** — and you must NEVER claim `php -l` passed or invent a lint result.

**Rule:** `php -l` BLOCKED must be stated explicitly in every report. Everything below is *ad-hoc verification*, not a canonical suite green.

## When to Use

- Any edit to PHP files (CMSNT/SHOPCLONE7 supplier/API adapters, views, crons, legacy apps) when `command -v php` / `where php` comes up empty.
- The system (or user) asks for verification evidence but the repo has no canonical test/lint command.
- Before handing off PHP work for deploy — state clearly that `php -l` must be run on a PHP-enabled machine.

> **[AUTO-TRIM NOTICE]**: Các mục quy tắc chi tiết mở rộng đã được lưu trữ trong thư mục `references/`.
> Tra cứu sâu từng chuyên đề bằng `skill_view(name='<skill>', file_path='references/<file>.md')`.
