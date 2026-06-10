# TaskBrain Finance

TaskBrain Finance is a self-hosted personal finance dashboard designed to run locally on a Raspberry Pi or home-network machine. It adds a financial intelligence module to TaskBrain with a FastAPI backend, React dashboard, SQLite storage, Plaid integration, and optional OpenAI-powered summaries.

This project is built for read-only personal financial analysis. It does not initiate payments, transfers, account verification flows, or money movement of any kind.

## Current Scope

- Local FastAPI backend under `finance/backend`
- Local React/Vite frontend under `finance/frontend`
- SQLite database for the first implementation
- Plaid Link sandbox connection flow with production-linking safety lock
- Encrypted Plaid access-token storage
- Plaid disconnect/delete control for revoking access and removing local synced data
- Account, transaction, recurring-stream, cash-flow, planning, and sync foundations
- Dashboard views for net worth, cash flow, future expenses, financial goals, projections, and AI recommendations
- OpenAI analysis modes for daily reviews, detailed reviews, and initial/yearly deep baseline reviews
- Daily sync scaffolding for cron/systemd deployment

## Plaid Products

The intended Plaid production products are limited to read-only personal finance data:

- Transactions: checking, savings, credit cards, and transaction history
- Investments: investment and retirement holdings/transactions where supported
- Liabilities: credit cards, student loans, mortgages, and loan details where supported

The app does not request Plaid Payments, Transfer, Auth, Identity, Signal, or other money-movement or verification products.

## Security Model

- Runs locally on the user's home network
- Remote access should be through Tailscale or another private network, not public port forwarding
- API keys and secrets are loaded from environment variables
- The backend refuses to start with placeholder signing/encryption secrets
- `.env`, SQLite databases, local state, build output, and dependency folders are ignored by git
- Plaid access tokens are encrypted before being stored in SQLite
- Plaid access tokens are never exposed to the browser
- Production Plaid linking requires both `PLAID_ENV=production` and `PLAID_ALLOW_PRODUCTION_LINKING=true`
- OpenAI analysis receives sanitized financial context only, not raw secrets, Plaid tokens, API keys, account numbers, or unnecessary transaction detail
- Deep AI analysis is intended for initial setup after linking institutions, then occasional yearly baseline updates

## Repository Layout

```text
finance/
  backend/    FastAPI app, SQLAlchemy models, migrations, sync jobs
  frontend/   React/Vite dashboard
docs/         Architecture and setup notes
deploy/       Example local deployment files
```

The finance module is isolated in `finance/` so it can be developed, tested, and deployed independently from the older TaskBrain task dashboard.

## Local Development

Backend:

```bash
cd finance/backend
cp .env.example .env
python -m venv ../../.venv
../../.venv/bin/pip install -e .
../../.venv/bin/python -m alembic upgrade head
../../.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8090
```

Frontend:

```bash
cd finance/frontend
npm install
npm run dev
```

Open the dashboard at:

```text
http://127.0.0.1:5173
```

## Production Notes

For a Raspberry Pi deployment, use a local reverse proxy such as Caddy or Nginx, bind the FastAPI service to localhost, and access the app remotely through Tailscale. Keep the database and `.env` file outside any public web root and back them up with local encryption.

Before enabling real Plaid connections, run:

```bash
./.venv/bin/python finance/backend/scripts/local_security_check.py
```

## License

No open-source license has been selected yet. The code is visible for review, but all rights are reserved unless a license is added later.
