# TaskBrain Finance Privacy Policy

Last updated: June 10, 2026

TaskBrain Finance is a self-hosted personal finance dashboard for organizing account balances, transactions, recurring expenses, investments, debts, planned expenses, cash flow, and net worth. It is intended to run locally on a private machine and is not designed for public internet exposure.

## Data Collected With Consent

When an institution is connected through Plaid Link, TaskBrain Finance may receive:

- Account metadata, including account names, types, subtypes, and institution identifiers.
- Account balances and historical balance snapshots.
- Transactions and transaction categories.
- Recurring transaction streams, including recurring deposits, subscriptions, and bills.
- Investment holdings and investment transactions.
- Liability information, such as loan balances, credit card balances, APRs, and payment details when available.

The app may also store data entered directly by the user, including planned future expenses, financial goals, budget categories, forecast assumptions, and notes.

## How Data Is Used

Financial data is used to provide local dashboards, charts, budget tracking, cash flow forecasts, debt and investment views, net worth history, recurring expense summaries, and personal financial recommendations.

TaskBrain Finance does not initiate payments, transfers, account changes, or trades.

## Storage And Security

TaskBrain Finance stores application data locally in SQLite on the machine running the application. Plaid access tokens and other sensitive integration tokens are encrypted before storage using an application encryption key. API keys and application secrets are loaded from environment variables and are not committed to the public code repository.

The intended deployment model is a private home network or private remote access through Tailscale or a similar encrypted private network. The application should not be exposed directly to the public internet.

## Sharing And AI Analysis

TaskBrain Finance does not sell consumer financial data.

Plaid is used to retrieve financial data after consent through Plaid Link. OpenAI may be used to generate daily reviews, detailed analyses, and initial or yearly baseline analyses from selected financial context. Prompts should avoid unnecessary sensitive identifiers where possible, and should not include Plaid access tokens, API keys, account numbers, or login credentials.

## Retention And Deletion

Data remains on the local system until it is deleted by the owner/operator. The application includes a disconnect and delete control for Plaid Items. When used, the backend attempts to revoke the Plaid Item and then removes the associated local accounts, balances, transactions, recurring streams, snapshots, sync history, and generated AI summaries.

Because this is a self-hosted application, the owner/operator can also remove local database files directly. A more formal periodically reviewed retention schedule is planned before any broader multi-user release.

## Contact

Questions about this privacy policy or data handling can be sent to dustin.varcoe@outlook.com.
