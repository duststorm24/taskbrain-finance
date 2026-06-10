# Security Notes

TaskBrain Finance handles sensitive personal financial data, so the default operating model is local-first and read-only.

## Intended Deployment

- Run the backend on `127.0.0.1` or a private LAN address.
- Use Tailscale for remote access.
- Do not expose the FastAPI backend directly to the public internet.
- Do not commit `.env`, SQLite databases, logs, build output, or dependency folders.

## Secrets

Secrets must be stored in environment variables or an uncommitted `.env` file:

- `OPENAI_API_KEY`
- `PLAID_CLIENT_ID`
- `PLAID_SECRET`
- `TASKBRAIN_FINANCE_SESSION_SECRET`
- `TASKBRAIN_FINANCE_TOKEN_ENCRYPTION_KEY`

The committed `.env.example` file contains placeholders only.

The backend validates startup settings and refuses to run with placeholder session-signing or token-encryption secrets.

## Plaid Token Handling

- The browser receives only Plaid Link tokens and public-token exchange responses needed for the connection flow.
- Plaid access tokens are exchanged and stored only by the backend.
- Plaid access tokens are encrypted before database storage.
- Plaid access tokens should never be logged, printed, returned in API responses, or sent to OpenAI.

## OpenAI Data Handling

OpenAI features should use summarized and aggregated financial facts whenever possible. Avoid sending unnecessary raw transaction detail, account numbers, Plaid tokens, API keys, session secrets, or database records that are not needed for the requested analysis.

## Product Boundaries

This app is for read-only personal financial analysis. It does not initiate payments, transfers, ACH flows, account verification, or money movement.

## Reporting Issues

If this repository becomes public and you notice a security concern, open a GitHub issue with a high-level description only. Do not include real API keys, Plaid tokens, account numbers, or private financial data in an issue.
