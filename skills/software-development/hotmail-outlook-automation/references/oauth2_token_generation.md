# Hotmail OAuth2 Refresh Token Generation & Graph API Verification

## 1. OAuth2 Parameters & Endpoints

- **Standard Client ID**: `9e5f94bc-e8a4-4e73-b8be-63364c29d753` (dùng cho consumer Outlook/Hotmail).
- **Scope**: `https://graph.microsoft.com/Mail.Read offline_access`
- **Redirect URI**: `https://login.microsoftonline.com/common/oauth2/nativeclient`
- **Authorize URL**:
  ```
  https://login.microsoftonline.com/common/oauth2/v2.0/authorize?client_id=9e5f94bc-e8a4-4e73-b8be-63364c29d753&response_type=code&redirect_uri=https://login.microsoftonline.com/common/oauth2/nativeclient&scope=https://graph.microsoft.com/Mail.Read%20offline_access&prompt=login&login_hint={email}
  ```

## 2. Token Exchange & Refresh Flow

- **Token Endpoint**: `POST https://login.microsoftonline.com/common/oauth2/v2.0/token`
- **Exchange Code for Refresh Token**:
  - `client_id`: `9e5f94bc-e8a4-4e73-b8be-63364c29d753`
  - `grant_type`: `authorization_code`
  - `code`: `{authorization_code_from_redirect}`
  - `redirect_uri`: `https://login.microsoftonline.com/common/oauth2/nativeclient`
  - `scope`: `https://graph.microsoft.com/Mail.Read offline_access`
- **Get Access Token from Refresh Token**:
  - `client_id`: `9e5f94bc-e8a4-4e73-b8be-63364c29d753`
  - `grant_type`: `refresh_token`
  - `refresh_token`: `{refresh_token}`
  - `scope`: `https://graph.microsoft.com/Mail.Read offline_access`

## 3. Microsoft Graph API OTP Reading

- **Messages Endpoint**: `GET https://graph.microsoft.com/v1.0/me/messages`
  - Header: `Authorization: Bearer {access_token}`
  - Query Params: `$top=5&$select=subject,from,receivedDateTime&$orderby=receivedDateTime desc`
- **Body / OTP Extraction**:
  - Regex: `\b\d{6}\b` trong `subject` hoặc HTML body qua `GET https://graph.microsoft.com/v1.0/me/messages/{id}`.

## 4. Farm Android Machine & Proxy Consistency

- Khi chạy authorize flow trên thiết bị farm (ví dụ Máy 10), luôn kiểm tra proxy máy:
  ```bash
  adb -s {serial} shell settings get global http_proxy
  ```
- Định tuyến requests session hoặc mở trực tiếp Chrome trên thiết bị qua proxy đó để đồng nhất IP mạng, hạn chế tối đa checkpoint / bot verification của Microsoft.
