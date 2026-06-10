# Plaid Sandbox Setup For TaskBrain Finance

Use the clean development browser profile, not the old MSU-linked Safari session.

## 1. Create Or Open Plaid Developer Account

Go to:

https://dashboard.plaid.com/signup

Use a personal or business email you control.

## 2. Find Sandbox Credentials

In the Plaid dashboard, look for API credentials.

You need:

- `client_id`
- Sandbox `secret`

Do not use Development or Production credentials yet.

## 3. Save Credentials Locally

Do not paste credentials into chat.

When ready:

1. Copy the Plaid `client_id`.
2. Tell Codex: `Plaid client id copied`.
3. Copy the Plaid Sandbox `secret`.
4. Tell Codex: `Plaid sandbox secret copied`.

Codex can then write each clipboard value into:

```text
finance/backend/.env
```

The expected values are:

```text
PLAID_ENV=sandbox
PLAID_CLIENT_ID=...
PLAID_SANDBOX_SECRET=...
```

If production access is approved, store the production credential separately:

```text
PLAID_PRODUCTION_SECRET=...
```

Leave `PLAID_ENV=sandbox` until you intentionally switch to real institutions.

## 4. Connect Test Institution

After credentials are saved and the backend restarts:

1. Open http://127.0.0.1:5173/
2. Create or sign into your local TaskBrain Finance user.
3. Click `Connect sandbox account`.
4. Use Plaid sandbox credentials/test institution when prompted.

The app encrypts Plaid access tokens before writing them to SQLite.
