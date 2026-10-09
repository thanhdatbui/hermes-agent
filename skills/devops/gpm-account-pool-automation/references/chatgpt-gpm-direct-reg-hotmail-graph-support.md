# Hotmail & Microsoft Graph Integration in ChatGPT GPM Direct Reg

## Overview
When registering ChatGPT on GPM profiles using Hotmail/Outlook accounts instead of Gmail:
1. Do not use Gmail browser automation to read verification codes.
2. Direct registration must use **Microsoft Graph API** (`https://graph.microsoft.com/v1.0/me/messages`) via OAuth refresh tokens to read OTP codes programmatically without opening Outlook web tabs.

## Hotmail Credentials File Contract
- File location: `D:\Taadaa\Hotmail\hotmail_input.txt`
- Format: pipe-delimited text (`mail|pass|refresh_token|client_id`)
- Example:
  `djricharalfr@hotmail.com|lynnlbah1|M.C508_BAY.0.U.MsaArtifacts...|9e5f94bc-e8a4-4e73-b8be-63364c29d753`

## CLI Parameters in `chatgpt_gpm_direct_reg.py`
- `--provider {gmail,hotmail}` (default `gmail`): Selects candidate domain filter (`@gmail.com` vs `@hotmail.com`) and switches the OTP mechanism.
- `--profile-id <id>`: Targets a specific GPM profile ID directly, bypassing full candidate scan.
- `--email <email>`: Filters to a specific email address.
- `--dry-run`: Validates candidate matching, credential lookup, and profile resolution without launching GPM browser.

## Graph API OTP Reading Protocol
1. **Token Refresh Endpoint**:
   - `POST https://login.microsoftonline.com/common/oauth2/v2.0/token`
   - Scopes tried in order:
     - `https://graph.microsoft.com/Mail.Read offline_access`
     - `Mail.Read offline_access`
     - `https://graph.microsoft.com/Mail.Read openid profile offline_access`
   - Fallback Client IDs:
     - Shop-provided client ID (primary)
     - `d3590ed6-52b3-4102-aeff-aad2292ab01c` (Microsoft Office)
     - `1b730954-1685-4b74-9bfd-dac224a7b894` (Azure CLI)
     - `1950a258-227b-4e31-a9cf-717495945fc2` (Azure PowerShell)

2. **Message Retrieval & OTP Extraction**:
   - `GET https://graph.microsoft.com/v1.0/me/messages?$top=10&$select=id,subject,from,receivedDateTime&$orderby=receivedDateTime desc`
   - Filter messages where subject or sender contains `openai` or `chatgpt`.
   - Fetch detail: `GET https://graph.microsoft.com/v1.0/me/messages/{id}?$select=subject,from,receivedDateTime,body,bodyPreview`.
   - Strip HTML tags and run regex `\b(\d{6})\b` to extract the 6-digit verification code.
